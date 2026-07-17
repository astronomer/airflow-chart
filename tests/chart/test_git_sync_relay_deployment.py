from subprocess import CalledProcessError

import pytest

from tests import git_root_dir, supported_k8s_versions
from tests.utils import get_containers_by_name, get_env_vars_dict
from tests.utils.chart import render_chart

readinessProbe = {"httpGet": {"initialDelaySeconds": 20, "periodSeconds": 20, "path": "/rhealthz", "port": 8080, "scheme": "HTTP"}}
livenessProbe = {"httpGet": {"initialDelaySeconds": 20, "periodSeconds": 20, "path": "/chealthz", "port": 8080, "scheme": "HTTP"}}
startupProbe = {"httpGet": {"initialDelaySeconds": 20, "periodSeconds": 20, "path": "/shealthz", "port": 8080, "scheme": "HTTP"}}


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayDeployment:
    def test_gsr_deployment_default(self, kube_version):
        """Test that no git-sync-relay templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only=[x.relative_to(git_root_dir) for x in (git_root_dir / "templates/git-sync-relay").glob("*")],
        )
        assert len(docs) == 0

    def test_gsr_deployment_gsr_enabled_with_defaults(self, kube_version):
        """Test that a valid deployment is rendered when git-sync-relay is enabled with defaults."""
        values = {"gitSyncRelay": {"enabled": True}}

        docs = render_chart(
            kube_version=kube_version,
            show_only=[
                "templates/git-sync-relay/git-sync-relay-deployment.yaml",
                "templates/git-sync-relay/git-sync-relay-pvc.yaml",
            ],
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 2
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
        assert c_by_name["git-daemon"]["image"].startswith("quay.io/astronomer/ap-git-daemon:")
        assert c_by_name["git-daemon"]["livenessProbe"]
        assert c_by_name["git-daemon"]["startupProbe"]
        # git-sync has no hardcoded probe fallback (customer-configurable only), unlike git-daemon
        assert "livenessProbe" not in c_by_name["git-sync"]
        assert "readinessProbe" not in c_by_name["git-sync"]
        assert "startupProbe" not in c_by_name["git-sync"]
        assert "annotations" not in doc["metadata"]
        assert "annotations" not in doc["spec"]["template"]["metadata"]

        git_dameon_env = get_env_vars_dict(c_by_name["git-daemon"].get("env"))
        assert not git_dameon_env.get("GIT_SYNC_REPO_FETCH_MODE")
        assert not git_dameon_env.get("GIT_SYNC_WEBHOOK_SECRET")
        git_sync_env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert git_sync_env.get("GIT_SYNC_REPO_FETCH_MODE") == "poll"
        assert not git_sync_env.get("GIT_SYNC_WEBHOOK_SECRET")
        spec = docs[0]["spec"]["template"]["spec"]
        assert spec["nodeSelector"] == {}
        assert spec["affinity"] == {}
        assert spec["tolerations"] == []
        # Private-CA trust is off unless global.privateCaCerts is set.
        assert "etc-ssl-certs" not in {v["name"] for v in spec["volumes"]}
        assert "etc-ssl-certs-copier" not in {c["name"] for c in spec.get("initContainers", [])}
        assert "UPDATE_CA_CERTS" not in git_sync_env
        git_sync_mounts = {m["name"] for m in c_by_name["git-sync"].get("volumeMounts", [])}
        assert "etc-ssl-certs" not in git_sync_mounts

    def test_gsr_deployment_private_ca_enabled(self, kube_version):
        """When global.privateCaCerts is set, the git-sync container trusts the CA(s):
        a writable /etc/ssl/certs emptyDir (seeded by an initContainer), the CA secret
        mounted under /usr/local/share/ca-certificates, and UPDATE_CA_CERTS=true."""
        values = {
            "gitSyncRelay": {"enabled": True},
            "global": {"privateCaCerts": ["my-private-ca"]},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only=["templates/git-sync-relay/git-sync-relay-deployment.yaml"],
            values=values,
        )
        assert len(docs) == 1
        spec = docs[0]["spec"]["template"]["spec"]

        # Volumes: writable trust-store overlay + the CA secret.
        vols = {v["name"]: v for v in spec["volumes"]}
        assert "etc-ssl-certs" in vols and "emptyDir" in vols["etc-ssl-certs"]
        # Volume name is derived from the list index (DNS-1123-safe), not the raw
        # Secret name; the Secret name stays on secretName.
        assert vols["private-ca-0"]["secret"]["secretName"] == "my-private-ca"

        # initContainer seeds the emptyDir from the image trust store.
        inits = {c["name"]: c for c in spec["initContainers"]}
        assert "etc-ssl-certs-copier" in inits
        copier_mounts = {m["name"]: m for m in inits["etc-ssl-certs-copier"]["volumeMounts"]}
        assert copier_mounts["etc-ssl-certs"]["mountPath"] == "/etc/ssl/certs_copy"

        # git-sync container: writable trust store + CA mount + UPDATE_CA_CERTS.
        c_by_name = get_containers_by_name(docs[0])
        gs_mounts = {m["name"]: m for m in c_by_name["git-sync"]["volumeMounts"]}
        assert gs_mounts["etc-ssl-certs"]["mountPath"] == "/etc/ssl/certs"
        # PEM content mounted with a .pem name; ap-base's update-ca-certificates picks it up.
        assert gs_mounts["private-ca-0"]["mountPath"] == "/usr/local/share/ca-certificates/private-ca-0.pem"
        assert gs_mounts["private-ca-0"]["subPath"] == "cert.pem"
        git_sync_env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert git_sync_env["UPDATE_CA_CERTS"] == "true"

    def test_gsr_deployment_private_ca_names_are_index_based(self, kube_version):
        """Volume names are index-derived (private-ca-N), so a Secret name that is
        not a valid volume name (e.g. contains a dot) or would collide is handled.
        Each CA maps to its own indexed volume + matching .crt mount."""
        values = {
            "gitSyncRelay": {"enabled": True},
            # Dotted Secret names are valid Secret names but invalid volume names.
            "global": {"privateCaCerts": ["corp.root.ca", "corp.intermediate.ca"]},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only=["templates/git-sync-relay/git-sync-relay-deployment.yaml"],
            values=values,
        )
        spec = docs[0]["spec"]["template"]["spec"]

        vols = {v["name"]: v for v in spec["volumes"]}
        assert vols["private-ca-0"]["secret"]["secretName"] == "corp.root.ca"
        assert vols["private-ca-1"]["secret"]["secretName"] == "corp.intermediate.ca"

        gs_mounts = {m["name"]: m for m in get_containers_by_name(docs[0])["git-sync"]["volumeMounts"]}
        assert gs_mounts["private-ca-0"]["mountPath"] == "/usr/local/share/ca-certificates/private-ca-0.pem"
        assert gs_mounts["private-ca-1"]["mountPath"] == "/usr/local/share/ca-certificates/private-ca-1.pem"

    def test_gsr_deployment_gsr_repo_share_mode_volume(self, kube_version):
        """Test that a valid deployment is rendered when git-sync-relay is enabled with repoShareMode=shared_volume."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "volumeSync": {"storageClassName": "my-usb-thumb-drive"},
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only=[
                "templates/git-sync-relay/git-sync-relay-deployment.yaml",
                "templates/git-sync-relay/git-sync-relay-pvc.yaml",
            ],
            values=values,
        )
        assert len(docs) == 2
        deployment, pvc = docs if docs[0]["kind"] == "Deployment" else docs[::-1]
        assert deployment["kind"] == "Deployment"
        assert deployment["apiVersion"] == "apps/v1"
        assert deployment["metadata"]["name"] == "release-name-git-sync-relay"
        assert pvc["kind"] == "PersistentVolumeClaim"
        assert pvc["kind"] == "PersistentVolumeClaim"
        assert pvc["spec"]["storageClassName"] == "my-usb-thumb-drive"
        c_by_name = get_containers_by_name(deployment)
        assert not c_by_name.get("git-daemon")
        assert len(c_by_name) == 1
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")

    def test_gsr_deployment_with_ssh_credentials_and_known_hosts(self, kube_version):
        """Test that a valid deployment is rendered when enabling git-sync with ssh credentials and known hosts and other custom configs."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "not-the-default-url",
                    "branch": "not-the-default-branch",
                    "depth": 22,
                    "wait": 333,
                    "subPath": "not-the-default-subPath",
                    "sshPrivateKeySecretName": "a-custom-secret-name",
                    "knownHosts": "not-the-default-knownHosts",
                },
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 2
        assert doc["spec"]["template"]["spec"]["volumes"] == [
            {"name": "git-sync-home", "emptyDir": {}},
            {"name": "git-repo-contents", "emptyDir": {}},
            {"name": "git-secret", "secret": {"secretName": "a-custom-secret-name"}},
            {"name": "release-name-git-sync-config", "configMap": {"name": "release-name-git-sync-config"}},
            {"name": "tmp", "emptyDir": {}},
        ]
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
        assert c_by_name["git-daemon"]["image"].startswith("quay.io/astronomer/ap-git-daemon:")
        assert c_by_name["git-sync"]["volumeMounts"] == [
            {"name": "git-sync-home", "mountPath": "/home/git-sync"},
            {"name": "git-secret", "mountPath": "/etc/git-secret/ssh", "readOnly": True, "subPath": "gitSshKey"},
            {
                "name": "release-name-git-sync-config",
                "mountPath": "/etc/git-secret/known_hosts",
                "readOnly": True,
                "subPath": "known_hosts",
            },
            {"name": "git-repo-contents", "mountPath": "/git"},
            {"name": "tmp", "mountPath": "/tmp"},  # noqa: S108
        ]
        assert get_env_vars_dict(c_by_name["git-sync"].get("env")) == {
            "GIT_SYNC_ROOT": "/git",
            "GIT_SYNC_REPO": "not-the-default-url",
            "GIT_SYNC_BRANCH": "not-the-default-branch",
            "GIT_SYNC_DEPTH": "22",
            "GIT_SYNC_WAIT": "333",
            "GIT_SYNC_SSH": "true",
            "GIT_SSH_KEY_FILE": "/etc/git-secret/ssh",
            "GIT_KNOWN_HOSTS": "true",
            "GIT_SSH_KNOWN_HOSTS_FILE": "/etc/git-secret/known_hosts",
            "GIT_SYNC_REPO_FETCH_MODE": "poll",
        }
        assert c_by_name["git-daemon"]["livenessProbe"]
        assert c_by_name["git-daemon"]["startupProbe"]

    def test_gsr_deployment_https_pat(self, kube_version):
        """HTTPS+PAT auth: GIT_SYNC_AUTH_TYPE is set, the credentials Secret mounts as a
        directory at /etc/git-secret/https, and no SSH env/mounts are present (PINF-425)."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "https://github.com/example/dags.git",
                    "auth": {
                        "type": "https-pat",
                        "https": {"credentialsSecretName": "release-name-git-sync"},
                    },
                },
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        c_by_name = get_containers_by_name(doc)

        volumes = doc["spec"]["template"]["spec"]["volumes"]
        https_vol = next(v for v in volumes if v["name"] == "git-https-secret")
        assert https_vol["secret"]["secretName"] == "release-name-git-sync"
        # The SSH secret volume must not be present in HTTPS mode.
        assert not any(v["name"] == "git-secret" for v in volumes)

        mounts = c_by_name["git-sync"]["volumeMounts"]
        https_mount = next(m for m in mounts if m["name"] == "git-https-secret")
        assert https_mount["mountPath"] == "/etc/git-secret/https"
        assert https_mount["readOnly"] is True

        env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert env["GIT_SYNC_AUTH_TYPE"] == "https-pat"
        assert env["GIT_SYNC_HTTPS_SECRET_DIR"] == "/etc/git-secret/https"
        assert "GIT_SYNC_SSH" not in env
        assert "GIT_SSH_KEY_FILE" not in env

    def test_gsr_deployment_https_pat_mount_has_no_subpath(self, kube_version):
        """Regression guard (FR2.2): the HTTPS credentials mount must NOT use subPath, so
        kubelet propagates rotated credentials without a pod restart."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "https://github.com/example/dags.git",
                    "auth": {
                        "type": "https-pat",
                        "https": {"credentialsSecretName": "release-name-git-sync"},
                    },
                },
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        c_by_name = get_containers_by_name(docs[0])
        https_mount = next(m for m in c_by_name["git-sync"]["volumeMounts"] if m["name"] == "git-https-secret")
        assert "subPath" not in https_mount

    def test_gsr_deployment_https_none(self, kube_version):
        """https-none (public repo): GIT_SYNC_AUTH_TYPE is set but no credentials are mounted."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "https://github.com/example/public-dags.git",
                    "auth": {"type": "https-none"},
                },
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        doc = docs[0]
        c_by_name = get_containers_by_name(doc)
        volumes = doc["spec"]["template"]["spec"]["volumes"]
        assert not any(v["name"] == "git-https-secret" for v in volumes)

        env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert env["GIT_SYNC_AUTH_TYPE"] == "https-none"
        assert "GIT_SYNC_HTTPS_SECRET_DIR" not in env
        assert "GIT_SYNC_SSH" not in env

    def test_gsr_deployment_ssh_and_https_mutually_exclusive(self, kube_version):
        """Configuring both SSH and HTTPS auth must fail the render (PINF-425)."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "https://github.com/example/dags.git",
                    "sshPrivateKeySecretName": "an-ssh-secret",
                    "auth": {
                        "type": "https-pat",
                        "https": {"credentialsSecretName": "release-name-git-sync"},
                    },
                },
            }
        }
        with pytest.raises(CalledProcessError) as excinfo:
            render_chart(
                kube_version=kube_version,
                show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
                values=values,
            )
        # The message must point at the actually-conflicting fields, not imply that
        # repo.auth is HTTPS-only (repo.auth.type: ssh is valid and pairs with
        # sshPrivateKeySecretName on every SSH deployment).
        stderr = excinfo.value.stderr.decode("utf-8")
        assert "repo.sshPrivateKeySecretName cannot be combined with HTTPS auth" in stderr

    def test_gsr_deployment_ssh_secret_with_explicit_ssh_auth_type_renders(self, kube_version):
        """sshPrivateKeySecretName combined with auth.type: ssh is a valid SSH config and must
        render, not trip the SSH/HTTPS mutual-exclusivity check — this is the shape houston
        emits for SSH (auth.type=ssh alongside the key Secret) (PINF-425)."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "git@github.com:example/dags.git",
                    "sshPrivateKeySecretName": "an-ssh-secret",
                    "auth": {"type": "ssh"},
                },
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        c_by_name = get_containers_by_name(doc)
        # SSH wiring is present and no HTTPS credentials are mounted.
        volumes = doc["spec"]["template"]["spec"]["volumes"]
        assert any(v["name"] == "git-secret" for v in volumes)
        assert not any(v["name"] == "git-https-secret" for v in volumes)
        env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert env["GIT_SYNC_SSH"] == "true"
        assert env["GIT_SSH_KEY_FILE"] == "/etc/git-secret/ssh"
        assert "GIT_SYNC_HTTPS_SECRET_DIR" not in env

    def test_gsr_deployment_https_pat_without_secret_degrades(self, kube_version):
        """https-pat without credentialsSecretName degrades like SSH-without-key: it renders
        GIT_SYNC_AUTH_TYPE=https-pat with no credentials mount (relay starts and retries),
        rather than failing the render (PINF-425)."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "https://github.com/example/dags.git",
                    "auth": {"type": "https-pat"},
                },
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        c_by_name = get_containers_by_name(doc)
        assert not any(v["name"] == "git-https-secret" for v in doc["spec"]["template"]["spec"]["volumes"])
        assert not any(m["name"] == "git-https-secret" for m in c_by_name["git-sync"]["volumeMounts"])
        env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert env["GIT_SYNC_AUTH_TYPE"] == "https-pat"
        assert "GIT_SYNC_HTTPS_SECRET_DIR" not in env

    def test_gsr_deployment_secret_without_auth_type_is_ignored(self, kube_version):
        """A credentialsSecretName with no auth.type renders without wiring HTTPS (the secret
        is ignored, no failure) — SSH likewise never rejects a secret (PINF-425)."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "https://github.com/example/dags.git",
                    "auth": {"https": {"credentialsSecretName": "release-name-git-sync"}},
                },
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        c_by_name = get_containers_by_name(doc)
        assert not any(v["name"] == "git-https-secret" for v in doc["spec"]["template"]["spec"]["volumes"])
        env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert "GIT_SYNC_AUTH_TYPE" not in env

    def test_gsr_deployment_invalid_auth_type(self, kube_version):
        """An unrecognized auth.type value must fail the render (PINF-425)."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "https://github.com/example/dags.git",
                    "auth": {"type": "https-token"},
                },
            }
        }
        with pytest.raises(CalledProcessError):
            render_chart(
                kube_version=kube_version,
                show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
                values=values,
            )

    def test_gsr_deployment_https_none_with_secret_is_ignored(self, kube_version):
        """https-none with a credentialsSecretName renders as https-none with no credentials
        mounted (the secret is ignored, no failure) — public-repo mode (PINF-425)."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "https://github.com/example/public-dags.git",
                    "auth": {
                        "type": "https-none",
                        "https": {"credentialsSecretName": "release-name-git-sync"},
                    },
                },
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        c_by_name = get_containers_by_name(doc)
        assert not any(v["name"] == "git-https-secret" for v in doc["spec"]["template"]["spec"]["volumes"])
        env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert env["GIT_SYNC_AUTH_TYPE"] == "https-none"

    def test_gsr_deployment_without_ssh_credentials_and_known_hosts(self, kube_version):
        """Test that a valid deployment is rendered when enabling git-sync without ssh credentials."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "not-the-default-url",
                    "branch": "not-the-default-branch",
                    "depth": 22,
                    "wait": 333,
                    "subPath": "not-the-default-subPath",
                },
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 2
        assert doc["spec"]["template"]["spec"]["volumes"] == [
            {"name": "git-sync-home", "emptyDir": {}},
            {"name": "git-repo-contents", "emptyDir": {}},
            {"name": "release-name-git-sync-config", "configMap": {"name": "release-name-git-sync-config"}},
            {"name": "tmp", "emptyDir": {}},
        ]
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
        assert c_by_name["git-daemon"]["image"].startswith("quay.io/astronomer/ap-git-daemon:")
        assert c_by_name["git-sync"]["volumeMounts"] == [
            {"name": "git-sync-home", "mountPath": "/home/git-sync"},
            {"name": "git-repo-contents", "mountPath": "/git"},
            {"name": "tmp", "mountPath": "/tmp"},  # noqa: S108
        ]
        assert get_env_vars_dict(c_by_name["git-sync"].get("env")) == {
            "GIT_SYNC_ROOT": "/git",
            "GIT_SYNC_REPO": "not-the-default-url",
            "GIT_SYNC_BRANCH": "not-the-default-branch",
            "GIT_SYNC_DEPTH": "22",
            "GIT_SYNC_WAIT": "333",
            "GIT_SYNC_REPO_FETCH_MODE": "poll",
        }
        assert c_by_name["git-daemon"]["livenessProbe"]
        assert c_by_name["git-daemon"]["startupProbe"]

    def test_gsr_deployment_with_metrics_enabled(self, kube_version):
        """Test that metrics env vars are set when gitSyncRelay.metrics.enabled is true."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "metrics": {"enabled": True},
                "repo": {
                    "url": "not-the-default-url",
                    "branch": "not-the-default-branch",
                    "depth": 22,
                    "wait": 333,
                    "subPath": "not-the-default-subPath",
                },
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        git_sync_env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert git_sync_env["METRICS_ENABLED"] == "true"
        assert git_sync_env["STATSD_HOST"] == "release-name-statsd"
        assert git_sync_env["STATSD_PORT"] == "9125"
        assert git_sync_env["DEBUG"] == "false"

    def test_gsr_deployment_with_metrics_disabled(self, kube_version):
        """Test that metrics env vars are absent when gitSyncRelay.metrics.enabled is false (default)."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "not-the-default-url",
                    "branch": "not-the-default-branch",
                    "depth": 22,
                    "wait": 333,
                    "subPath": "not-the-default-subPath",
                },
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        c_by_name = get_containers_by_name(doc)
        git_sync_env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert "METRICS_ENABLED" not in git_sync_env
        assert "STATSD_HOST" not in git_sync_env
        assert "STATSD_PORT" not in git_sync_env
        assert "DEBUG" not in git_sync_env

    def test_gsr_deployment_with_resource_overrides(self, kube_version):
        """Test that gitsync relay deployment are configurable with custom resource limits."""
        resources = {
            "requests": {"cpu": 99.5, "memory": "777Mi"},
            "limits": {"cpu": 99.6, "memory": "888Mi"},
        }
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "gitSync": {"resources": resources},
                "gitDaemon": {"resources": resources},
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        assert c_by_name["git-sync"]["resources"] == resources
        assert c_by_name["git-daemon"]["resources"] == resources

    def test_gsr_deployment_with_securitycontext_overrides(self, kube_version):
        """Test that gitsync  deployment are configurable with custom securitycontext."""
        gsrsecuritycontext = {"fsGroup": 65533, "runAsUser": 12345, "privileged": True}
        values = {"gitSyncRelay": {"enabled": True, "securityContext": gsrsecuritycontext}}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        # runAsNonRoot: true and seccompProfile are PSS-Restricted chart defaults that merge in
        # alongside overrides (pod-level securityContext).
        assert doc["spec"]["template"]["spec"]["securityContext"] == {
            **gsrsecuritycontext,
            "runAsNonRoot": True,
            "seccompProfile": {"type": "RuntimeDefault"},
        }

    def test_gsr_deployment_openshift_strips_incompatible_security_context(self, kube_version):
        """Test that fsGroup and runAsUser are stripped from pod securityContext when OpenShift is enabled,
        even if a customer explicitly sets them."""
        values = {
            "openshift": {"enabled": True},
            "gitSyncRelay": {
                "enabled": True,
                "securityContext": {
                    "fsGroup": 65533,
                    "runAsUser": 50000,
                    "runAsNonRoot": True,
                },
            },
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        pod_security_context = doc["spec"]["template"]["spec"]["securityContext"]

        # fsGroup and runAsUser must be absent on OpenShift
        assert "fsGroup" not in pod_security_context
        assert "runAsUser" not in pod_security_context

        # runAsNonRoot must be preserved/enforced
        assert pod_security_context["runAsNonRoot"] is True

    def test_gsr_deployment_non_openshift_preserves_security_context(self, kube_version):
        """Test that fsGroup and runAsUser are preserved in pod securityContext when OpenShift is disabled."""
        gsrsecuritycontext = {"fsGroup": 65533, "runAsUser": 50000, "runAsNonRoot": True}
        values = {
            "openshift": {"enabled": False},
            "gitSyncRelay": {
                "enabled": True,
                "securityContext": gsrsecuritycontext,
            },
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        pod_security_context = doc["spec"]["template"]["spec"]["securityContext"]

        assert pod_security_context["fsGroup"] == 65533
        assert pod_security_context["runAsUser"] == 50000
        assert pod_security_context["runAsNonRoot"] is True

    def test_gsr_deployment_with_custom_registry_secret(self, kube_version):
        """Test git-sync-relay deployment with custom registry secret."""
        values = {
            "airflow": {"registry": {"secretName": "gscsecret"}},
            "gitSyncRelay": {"enabled": True},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        assert [{"name": "gscsecret"}] == doc["spec"]["template"]["spec"]["imagePullSecrets"]

    def test_gsr_deployment_with_custom_probes(self, kube_version):
        """Test git-sync-relay deployment with custom liveness, readiness, and startup probes."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "gitSync": {
                    "readinessProbe": readinessProbe,
                    "livenessProbe": livenessProbe,
                    "startupProbe": startupProbe,
                },
                "gitDaemon": {
                    "readinessProbe": readinessProbe,
                    "livenessProbe": livenessProbe,
                    "startupProbe": startupProbe,
                },
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        assert readinessProbe == c_by_name["git-daemon"]["readinessProbe"]
        assert livenessProbe == c_by_name["git-daemon"]["livenessProbe"]
        assert startupProbe == c_by_name["git-daemon"]["startupProbe"]
        assert readinessProbe == c_by_name["git-sync"]["readinessProbe"]
        assert livenessProbe == c_by_name["git-sync"]["livenessProbe"]
        assert startupProbe == c_by_name["git-sync"]["startupProbe"]

    def test_gsr_deployment_with_repo_fetch_mode_webhook(self, kube_version):
        """Test git-sync-relay deployment with repoFetchMode=webhook."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoFetchMode": "webhook",
                "webhookSecretKey": "be sure to drink your ovaltine",
            },
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )

        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert len(c_by_name) == 2
        git_sync_env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert git_sync_env["GIT_SYNC_REPO_FETCH_MODE"] == "webhook"
        assert git_sync_env["GIT_SYNC_WEBHOOK_SECRET"] == "be sure to drink your ovaltine"
        git_dameon_env = get_env_vars_dict(c_by_name["git-daemon"].get("env"))
        assert not git_dameon_env.get("GIT_SYNC_REPO_FETCH_MODE")
        assert not git_dameon_env.get("GIT_SYNC_WEBHOOK_SECRET")
        assert {"mountPath": "/tmp", "name": "tmp"} in c_by_name["git-sync"]["volumeMounts"]  # noqa: S108

    def test_git_sync_server_deployment_with_sidecar_and_authproxy_enabled(self, kube_version):
        """Test git sync server deployment with sidecar components."""
        values = {
            "gitSyncRelay": {"enabled": True, "repoFetchMode": "webhook"},
            "loggingSidecar": {"enabled": True},
            "authSidecar": {"enabled": True},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        assert doc["spec"]["template"]["spec"]["volumes"] == [
            {"name": "git-sync-home", "emptyDir": {}},
            {"name": "git-repo-contents", "emptyDir": {}},
            {"name": "release-name-git-sync-config", "configMap": {"name": "release-name-git-sync-config"}},
            {"name": "config-volume", "configMap": {"name": "release-name-sidecar-config"}},
            {"name": "sidecar-logging-consumer", "emptyDir": {}},
            {"name": "nginx-access-logs", "emptyDir": {}},
            {"name": "nginx-sidecar-conf", "configMap": {"name": "release-name-git-sync-relay-nginx-conf"}},
            {"name": "nginx-cache", "emptyDir": {}},
            {"name": "nginx-tmp", "emptyDir": {}},
            {"name": "tmp", "emptyDir": {}},
        ]

        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 4
        assert "git-sync" in c_by_name
        assert "git-daemon" in c_by_name
        assert "auth-proxy" in c_by_name
        assert "sidecar-log-consumer" in c_by_name
        assert c_by_name["git-sync"]["command"] == ["bash"]
        assert c_by_name["git-sync"]["args"] == [
            "-c",
            "/entrypoint.sh 1> >( tee -a /var/log/sidecar-logging-consumer/out.log ) 2> >( tee -a /var/log/sidecar-logging-consumer/err.log >&2 )",
        ]

        assert c_by_name["auth-proxy"]["volumeMounts"] == [
            {"mountPath": "/var/lib/nginx/logs", "name": "nginx-access-logs"},
            {"mountPath": "/etc/nginx/nginx.conf", "name": "nginx-sidecar-conf", "subPath": "nginx.conf"},
            {"mountPath": "/var/cache/nginx", "name": "nginx-cache"},
            {"mountPath": "/tmp", "name": "tmp"},  # noqa: S108
            {"mountPath": "/var/lib/nginx/tmp", "name": "nginx-tmp"},
        ]
        assert c_by_name["auth-proxy"]["livenessProbe"]
        assert c_by_name["auth-proxy"]["readinessProbe"]
        assert c_by_name["auth-proxy"]["startupProbe"]
        assert c_by_name["sidecar-log-consumer"]["startupProbe"]

    def test_git_sync_service_account_with_template(self, kube_version):
        """Test git-sync-relay service account with template."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "gitSyncRelay": {
                    "enabled": True,
                    "serviceAccount": {
                        "create": False,
                        "name": "custom-{{ .Release.Name }}-dag-processor",
                    },
                },
            },
            show_only=[
                "templates/git-sync-relay/git-sync-relay-deployment.yaml",
                "templates/git-sync-relay/git-sync-relay-serviceaccount.yaml",
            ],
        )
        assert len(docs) == 1
        service_accounts = [sa for sa in docs if sa.get("kind") == "ServiceAccount"]
        assert len(service_accounts) == 0
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"

    def test_git_sync_relay_airflow_affinity(self, kube_version, airflow_node_pool_config):
        """Test that git sync relay global airflow affinity, node pool and toleration configs."""
        values = {
            "airflow": {
                "nodeSelector": airflow_node_pool_config["nodeSelector"],
                "affinity": airflow_node_pool_config["affinity"],
                "tolerations": airflow_node_pool_config["tolerations"],
            },
            "gitSyncRelay": {"enabled": True},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        spec = docs[0]["spec"]["template"]["spec"]
        assert spec["affinity"] == airflow_node_pool_config["affinity"]
        assert spec["nodeSelector"] == airflow_node_pool_config["nodeSelector"]
        assert spec["tolerations"] == airflow_node_pool_config["tolerations"]

    def test_git_sync_relay_affinity(self, kube_version, airflow_node_pool_config):
        """Test that git sync relay affinity, node pool and toleration configs."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "nodeSelector": airflow_node_pool_config["nodeSelector"],
                "affinity": airflow_node_pool_config["affinity"],
                "tolerations": airflow_node_pool_config["tolerations"],
            },
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        spec = docs[0]["spec"]["template"]["spec"]
        assert spec["affinity"] == airflow_node_pool_config["affinity"]
        assert spec["nodeSelector"] == airflow_node_pool_config["nodeSelector"]
        assert spec["tolerations"] == airflow_node_pool_config["tolerations"]

    def test_gsr_annotations_overrides(self, kube_version):
        """Test that gitSyncRelay annotations are set when gitSyncRelay.annotations when passed."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values={"gitSyncRelay": {"enabled": True, "annotations": {"example.com/owner": "platform"}}},
        )
        assert len(docs) == 1
        assert docs[0]["metadata"]["annotations"] == {"example.com/owner": "platform"}

    def test_gsr_pod_annotations_overrides(self, kube_version):
        """Test that gitSyncRelay podAnnotations are set when gitSyncRelay.podAnnotations when passed."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values={"gitSyncRelay": {"enabled": True, "podAnnotations": {"sidecar.istio.io/inject": "false"}}},
        )
        assert len(docs) == 1
        assert docs[0]["spec"]["template"]["metadata"]["annotations"] == {"sidecar.istio.io/inject": "false"}
