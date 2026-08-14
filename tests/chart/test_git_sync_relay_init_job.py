from subprocess import CalledProcessError

import pytest

from tests import supported_k8s_versions
from tests.utils import get_containers_by_name, get_env_vars_dict
from tests.utils.chart import render_chart

show_only = "templates/git-sync-relay/git-sync-relay-init-job.yaml"


def _find_doc_by_kind(docs, kind):
    """Return the first doc matching the given kind."""
    for doc in docs:
        if doc["kind"] == kind:
            return doc
    raise AssertionError(f"No doc with kind={kind} found in {[d['kind'] for d in docs]}")


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayInitJob:
    def test_init_job_not_rendered_by_default(self, kube_version):
        """Test that the init job is not rendered when gitSyncRelay is disabled."""
        docs = render_chart(kube_version=kube_version, show_only=show_only)
        assert len(docs) == 0

    def test_init_job_not_rendered_when_git_daemon_mode(self, kube_version):
        """Test that the init job is not rendered when repoShareMode is git_daemon."""
        docs = render_chart(
            kube_version=kube_version,
            show_only=show_only,
            values={"gitSyncRelay": {"enabled": True, "repoShareMode": "git_daemon"}},
        )
        assert len(docs) == 0

    def test_init_job_rendered_with_shared_volume(self, kube_version):
        """Test that the init job is rendered when gitSyncRelay is enabled with shared_volume mode."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        assert len(docs) == 3
        kinds = sorted(d["kind"] for d in docs)
        assert kinds == ["Job", "PersistentVolumeClaim", "ServiceAccount"]

        doc = _find_doc_by_kind(docs, "Job")
        assert doc["apiVersion"] == "batch/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay-init"
        assert doc["metadata"]["annotations"]["helm.sh/hook"] == "pre-install,pre-upgrade"
        assert doc["metadata"]["annotations"]["helm.sh/hook-delete-policy"] == "before-hook-creation"
        assert doc["metadata"]["annotations"]["helm.sh/hook-weight"] == "5"

    def test_init_job_spec_defaults(self, kube_version):
        """Test Job spec has correct pod spec."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        assert doc["spec"]["template"]["spec"]["restartPolicy"] == "Never"

    def test_init_job_uses_git_sync_relay_image(self, kube_version):
        """Test that the init job uses the ap-git-sync-relay image, not upstream git-sync.

        Reusing the relay image (and its git-sync-once entrypoint, see
        test_init_job_runs_git_sync_once_command) means HTTPS+PAT auth goes through
        the relay's own credential helper instead of upstream git-sync's native auth,
        which would put the token in a plaintext env var (PINF-1190)."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        c_by_name = get_containers_by_name(doc, include_init_containers=True)
        assert "ap-git-sync-relay" in c_by_name["git-sync"]["image"]
        assert "ap-git-sync-relay" in c_by_name["git-config-manager"]["image"]

    def test_init_job_uses_full_security_context(self, kube_version):
        """The git-sync container must use the same hardened securityContext as the
        long-running Deployment (capabilities dropped, no privilege escalation), not
        just readOnlyRootFilesystem on its own."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        c_by_name = get_containers_by_name(doc)
        sc = c_by_name["git-sync"]["securityContext"]
        assert sc["readOnlyRootFilesystem"] is True
        assert sc["allowPrivilegeEscalation"] is False
        assert sc["capabilities"]["drop"] == ["ALL"]

    def test_init_job_has_active_deadline_seconds(self, kube_version):
        """The Job must bound its own runtime -- there's no in-process retry loop in a
        one-shot sync the way the long-running Deployment has."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        assert doc["spec"]["activeDeadlineSeconds"] == 300  # default gitSyncTimeout

    def test_init_job_active_deadline_seconds_configurable(self, kube_version):
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "repo": {"gitSyncTimeout": 900},
            }
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        assert doc["spec"]["activeDeadlineSeconds"] == 900

    def test_init_job_has_git_config_manager_init_container(self, kube_version):
        """Test that the init job includes the git-config-manager initContainer."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        c_by_name = get_containers_by_name(doc, include_init_containers=True)
        assert "git-config-manager" in c_by_name
        assert c_by_name["git-config-manager"]["command"] == [
            "git",
            "config",
            "--global",
            "--add",
            "safe.directory",
            "/git",
        ]
        mount_names = [m["name"] for m in c_by_name["git-config-manager"]["volumeMounts"]]
        assert "git-sync-home" in mount_names

    def test_init_job_runs_git_sync_once_command(self, kube_version):
        """Test that the container runs git-sync-once (git-sync-relay's one-shot
        entrypoint) via `args`, not `command` -- no command override, so the image's
        own entrypoint.sh still runs first (CA-trust/debug setup), then execs this
        instead of the default long-running Sanic daemon."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        c_by_name = get_containers_by_name(doc)
        assert "git-sync" in c_by_name
        assert c_by_name["git-sync"]["args"] == ["git-sync-once"]
        assert "command" not in c_by_name["git-sync"]

        env = get_env_vars_dict(c_by_name["git-sync"]["env"])
        assert "GIT_SYNC_ONE_TIME" not in env  # upstream git-sync's env var, unused by git-sync-relay
        assert env["GIT_SYNC_ROOT"] == "/git"

    def test_init_job_volumes(self, kube_version):
        """Test that the init job has the correct volumes and no sidecar volumes."""
        values = {
            "gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"},
            "loggingSidecar": {"enabled": True},
            "authSidecar": {"enabled": True},
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        volumes = doc["spec"]["template"]["spec"]["volumes"]
        volume_names = [v["name"] for v in volumes]
        assert "git-sync-home" in volume_names
        assert "git-repo-contents" in volume_names
        assert "tmp" in volume_names
        assert "config-volume" not in volume_names
        assert "sidecar-logging-consumer" not in volume_names
        assert "nginx-sidecar-conf" not in volume_names

        pvc_vol = next(v for v in volumes if v["name"] == "git-repo-contents")
        assert pvc_vol["persistentVolumeClaim"]["claimName"] == "git-repo-contents"

    def test_init_job_configmap_volume_with_known_hosts(self, kube_version):
        """Test that the git-sync-config ConfigMap volume is included when knownHosts is set."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "repo": {
                    "sshPrivateKeySecretName": "my-ssh-secret",
                    "knownHosts": "github.com ssh-rsa AAAA...",
                },
            }
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        volumes = doc["spec"]["template"]["spec"]["volumes"]
        volume_names = [v["name"] for v in volumes]
        assert "release-name-git-sync-config" in volume_names

    def test_init_job_configmap_volume_without_known_hosts(self, kube_version):
        """Test that the git-sync-config ConfigMap volume is NOT included when knownHosts is empty."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "repo": {"knownHosts": ""},
            }
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        volumes = doc["spec"]["template"]["spec"]["volumes"]
        volume_names = [v["name"] for v in volumes]
        assert "release-name-git-sync-config" not in volume_names

    def test_init_job_tmp_volume_mount(self, kube_version):
        """Test that the git-sync container mounts /tmp for readOnlyRootFilesystem."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        c_by_name = get_containers_by_name(doc)
        mounts = {m["name"]: m for m in c_by_name["git-sync"]["volumeMounts"]}
        assert "tmp" in mounts
        assert mounts["tmp"]["mountPath"] == "/tmp"  # noqa: S108

    def test_init_job_git_sync_home_volume_mount(self, kube_version):
        """Test that the git-sync container mounts git-sync-home."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        c_by_name = get_containers_by_name(doc)
        mount_names = [m["name"] for m in c_by_name["git-sync"]["volumeMounts"]]
        assert "git-sync-home" in mount_names
        assert "git-repo-contents" in mount_names

    def test_init_job_with_ssh_key(self, kube_version):
        """Test that SSH volumes and env vars are included when sshPrivateKeySecretName is set."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "repo": {
                    "sshPrivateKeySecretName": "my-ssh-secret",
                    "knownHosts": "",
                },
            }
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        volumes = doc["spec"]["template"]["spec"]["volumes"]
        volume_names = [v["name"] for v in volumes]
        assert "git-secret" in volume_names

        c_by_name = get_containers_by_name(doc)
        env = get_env_vars_dict(c_by_name["git-sync"]["env"])
        assert env["GIT_SYNC_SSH"] == "true"
        assert env["GIT_SSH_KEY_FILE"] == "/etc/git-secret/ssh"
        assert env["GIT_KNOWN_HOSTS"] == "false"

    def test_init_job_with_ssh_key_and_known_hosts(self, kube_version):
        """Test SSH with custom known_hosts."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "repo": {
                    "sshPrivateKeySecretName": "my-ssh-secret",
                    "knownHosts": "github.com ssh-rsa AAAA...",
                },
            }
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        c_by_name = get_containers_by_name(doc)
        env = get_env_vars_dict(c_by_name["git-sync"]["env"])
        assert env["GIT_KNOWN_HOSTS"] == "true"
        assert env["GIT_SSH_KNOWN_HOSTS_FILE"] == "/etc/git-secret/known_hosts"

    def test_init_job_no_probes(self, kube_version):
        """Test that the init job container has no liveness/readiness probes."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        c_by_name = get_containers_by_name(doc)
        assert "livenessProbe" not in c_by_name["git-sync"]
        assert "readinessProbe" not in c_by_name["git-sync"]

    def test_init_job_has_dedicated_hook_service_account(self, kube_version):
        """Test that a hook SA is created before the Job and the Job references it."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        assert len(docs) == 3

        sa_doc = _find_doc_by_kind(docs, "ServiceAccount")
        assert sa_doc["metadata"]["name"] == "release-name-git-sync-relay-init"
        assert sa_doc["metadata"]["annotations"]["helm.sh/hook"] == "pre-install,pre-upgrade"
        assert sa_doc["metadata"]["annotations"]["helm.sh/hook-weight"] == "3"

        job_doc = _find_doc_by_kind(docs, "Job")
        assert job_doc["spec"]["template"]["spec"]["serviceAccountName"] == "release-name-git-sync-relay-init"

    def test_init_job_has_hook_pvc(self, kube_version):
        """Test that a PVC is created as a pre-install/pre-upgrade hook before the Job.

        pre-upgrade matters so a release that newly enables shared_volume mode via
        `helm upgrade` (rather than at initial install) still gets the PVC created --
        without it, the Job would fail trying to mount a PVC that never got created.
        Safe to also fire on upgrade because the PVC's own render is lookup-gated (see
        test_init_job_pvc_lookup_gate_comment below): it only renders when the PVC
        doesn't already exist, so this never re-creates/destroys an existing one.
        """
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        assert len(docs) == 3

        pvc_doc = _find_doc_by_kind(docs, "PersistentVolumeClaim")
        assert pvc_doc["metadata"]["name"] == "git-repo-contents"
        assert pvc_doc["metadata"]["annotations"]["helm.sh/hook"] == "pre-install,pre-upgrade"
        assert pvc_doc["metadata"]["annotations"]["helm.sh/hook-delete-policy"] == "before-hook-creation"
        assert pvc_doc["metadata"]["annotations"]["helm.sh/hook-weight"] == "1"
        assert pvc_doc["spec"]["accessModes"] == ["ReadWriteMany"]

    def test_init_job_https_pat(self, kube_version):
        """HTTPS+PAT auth: GIT_SYNC_AUTH_TYPE is set, the credentials Secret mounts as a
        directory (no subPath, matching the Deployment) at /etc/git-secret/https, and no
        SSH env/mounts are present (PINF-1190)."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "repo": {
                    "url": "https://github.com/example/dags.git",
                    "auth": {
                        "type": "https-pat",
                        "https": {"credentialsSecretName": "release-name-git-sync"},
                    },
                },
            }
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")
        c_by_name = get_containers_by_name(doc)

        volumes = doc["spec"]["template"]["spec"]["volumes"]
        https_vol = next(v for v in volumes if v["name"] == "git-https-secret")
        assert https_vol["secret"]["secretName"] == "release-name-git-sync"
        assert not any(v["name"] == "git-secret" for v in volumes)

        mounts = c_by_name["git-sync"]["volumeMounts"]
        https_mount = next(m for m in mounts if m["name"] == "git-https-secret")
        assert https_mount["mountPath"] == "/etc/git-secret/https"
        assert https_mount["readOnly"] is True
        assert "subPath" not in https_mount

        env = get_env_vars_dict(c_by_name["git-sync"]["env"])
        assert env["GIT_SYNC_AUTH_TYPE"] == "https-pat"
        assert env["GIT_SYNC_HTTPS_SECRET_DIR"] == "/etc/git-secret/https"
        assert "GIT_SYNC_SSH" not in env
        assert "GIT_SSH_KEY_FILE" not in env

    def test_init_job_https_none(self, kube_version):
        """https-none (public repo, no credentials) sets GIT_SYNC_AUTH_TYPE with no
        credentials mount."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "repo": {
                    "url": "https://github.com/example/dags.git",
                    "auth": {"type": "https-none"},
                },
            }
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")
        c_by_name = get_containers_by_name(doc)

        assert not any(v["name"] == "git-https-secret" for v in doc["spec"]["template"]["spec"]["volumes"])
        env = get_env_vars_dict(c_by_name["git-sync"]["env"])
        assert env["GIT_SYNC_AUTH_TYPE"] == "https-none"
        assert "GIT_SYNC_HTTPS_SECRET_DIR" not in env

    def test_init_job_ssh_and_https_mutually_exclusive(self, kube_version):
        """Configuring both SSH and HTTPS auth must fail the render, same as the
        Deployment -- both templates share the gitSyncRelay.validateAuth helper."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
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
            render_chart(kube_version=kube_version, show_only=show_only, values=values)
        stderr = excinfo.value.stderr.decode("utf-8")
        assert "repo.sshPrivateKeySecretName cannot be combined with HTTPS auth" in stderr

    def test_init_job_invalid_auth_type(self, kube_version):
        """An unrecognized auth.type value must fail the render, same as the Deployment."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "repo": {
                    "url": "https://github.com/example/dags.git",
                    "auth": {"type": "https-token"},
                },
            }
        }
        with pytest.raises(CalledProcessError):
            render_chart(kube_version=kube_version, show_only=show_only, values=values)

    def test_init_job_backoff_limit_zero(self, kube_version):
        """A failed clone must surface immediately, not retry up to Kubernetes'
        default of 6 -- which would also make activeDeadlineSeconds bound a
        fraction of gitSyncTimeout per attempt instead of the full value."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        assert doc["spec"]["backoffLimit"] == 0

    def test_init_job_no_private_ca_by_default(self, kube_version):
        """Private-CA trust is off unless global.privateCaCerts is set."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")
        spec = doc["spec"]["template"]["spec"]

        assert "etc-ssl-certs" not in {v["name"] for v in spec["volumes"]}
        assert "etc-ssl-certs-copier" not in {c["name"] for c in spec.get("initContainers", [])}
        c_by_name = get_containers_by_name(doc)
        assert "UPDATE_CA_CERTS" not in get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert "etc-ssl-certs" not in {m["name"] for m in c_by_name["git-sync"].get("volumeMounts", [])}

    def test_init_job_private_ca_enabled(self, kube_version):
        """When global.privateCaCerts is set, the init Job's git-sync container trusts
        the CA(s) the same way the long-running Deployment does: a writable
        /etc/ssl/certs emptyDir (seeded by an initContainer), the CA secret mounted
        under /usr/local/share/ca-certificates, and UPDATE_CA_CERTS=true.

        Without this, a shared_volume deployment against a private-CA git host would
        have its bootstrap clone fail TLS validation even though the long-running
        Deployment (which does have this wiring) would work fine once it started."""
        values = {
            "gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"},
            "global": {"privateCaCerts": ["my-private-ca"]},
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")
        spec = doc["spec"]["template"]["spec"]

        vols = {v["name"]: v for v in spec["volumes"]}
        assert "etc-ssl-certs" in vols and "emptyDir" in vols["etc-ssl-certs"]
        assert vols["private-ca-0"]["secret"]["secretName"] == "my-private-ca"

        inits = {c["name"]: c for c in spec["initContainers"]}
        assert "etc-ssl-certs-copier" in inits
        copier_mounts = {m["name"]: m for m in inits["etc-ssl-certs-copier"]["volumeMounts"]}
        assert copier_mounts["etc-ssl-certs"]["mountPath"] == "/etc/ssl/certs_copy"
        # The copier must run before git-config-manager so the trust store is seeded
        # before anything else in the pod might need it.
        init_names = [c["name"] for c in spec["initContainers"]]
        assert init_names.index("etc-ssl-certs-copier") < init_names.index("git-config-manager")

        c_by_name = get_containers_by_name(doc)
        gs_mounts = {m["name"]: m for m in c_by_name["git-sync"]["volumeMounts"]}
        assert gs_mounts["etc-ssl-certs"]["mountPath"] == "/etc/ssl/certs"
        assert gs_mounts["private-ca-0"]["mountPath"] == "/usr/local/share/ca-certificates/private-ca-0.pem"
        assert gs_mounts["private-ca-0"]["subPath"] == "cert.pem"
        env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert env["UPDATE_CA_CERTS"] == "true"

    def test_init_job_uses_openshift_pod_security_context_helper(self, kube_version):
        """fsGroup/runAsUser must be stripped on OpenShift, same as the Deployment --
        the Job must use the gitSyncRelay.podSecurityContext helper, not a raw toYaml
        of gitSyncRelay.securityContext which bypasses that stripping entirely."""
        values = {
            "openshift": {"enabled": True},
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "securityContext": {"fsGroup": 65533, "runAsUser": 50000, "runAsNonRoot": True},
            },
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")
        pod_security_context = doc["spec"]["template"]["spec"]["securityContext"]

        assert "fsGroup" not in pod_security_context
        assert "runAsUser" not in pod_security_context
        assert pod_security_context["runAsNonRoot"] is True

    def test_init_job_non_openshift_preserves_security_context(self, kube_version):
        """fsGroup/runAsUser must be preserved when OpenShift is disabled."""
        values = {
            "openshift": {"enabled": False},
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "securityContext": {"fsGroup": 65533, "runAsUser": 50000, "runAsNonRoot": True},
            },
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")
        pod_security_context = doc["spec"]["template"]["spec"]["securityContext"]

        assert pod_security_context["fsGroup"] == 65533
        assert pod_security_context["runAsUser"] == 50000
        assert pod_security_context["runAsNonRoot"] is True

    def test_init_job_airflow_scheduling_fields(self, kube_version, airflow_node_pool_config):
        """The Job must respect global airflow nodeSelector/affinity/tolerations, same as
        the Deployment -- without this it could schedule onto nodes that violate cluster
        scheduling constraints the rest of the release respects."""
        values = {
            "airflow": {
                "nodeSelector": airflow_node_pool_config["nodeSelector"],
                "affinity": airflow_node_pool_config["affinity"],
                "tolerations": airflow_node_pool_config["tolerations"],
            },
            "gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"},
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        spec = _find_doc_by_kind(docs, "Job")["spec"]["template"]["spec"]

        assert spec["affinity"] == airflow_node_pool_config["affinity"]
        assert spec["nodeSelector"] == airflow_node_pool_config["nodeSelector"]
        assert spec["tolerations"] == airflow_node_pool_config["tolerations"]

    def test_init_job_gitsyncrelay_scheduling_fields_override_airflow(self, kube_version, airflow_node_pool_config):
        """gitSyncRelay-specific scheduling values take precedence over the global airflow ones."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "nodeSelector": airflow_node_pool_config["nodeSelector"],
                "affinity": airflow_node_pool_config["affinity"],
                "tolerations": airflow_node_pool_config["tolerations"],
            },
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        spec = _find_doc_by_kind(docs, "Job")["spec"]["template"]["spec"]

        assert spec["affinity"] == airflow_node_pool_config["affinity"]
        assert spec["nodeSelector"] == airflow_node_pool_config["nodeSelector"]
        assert spec["tolerations"] == airflow_node_pool_config["tolerations"]

    def test_init_job_termination_grace_period(self, kube_version):
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "terminationGracePeriodSeconds": 45,
            },
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        spec = _find_doc_by_kind(docs, "Job")["spec"]["template"]["spec"]

        assert spec["terminationGracePeriodSeconds"] == 45
