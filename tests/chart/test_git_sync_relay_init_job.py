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
        """Test that a PVC is created as a pre-install hook before the Job."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        assert len(docs) == 3

        pvc_doc = _find_doc_by_kind(docs, "PersistentVolumeClaim")
        assert pvc_doc["metadata"]["name"] == "git-repo-contents"
        assert pvc_doc["metadata"]["annotations"]["helm.sh/hook"] == "pre-install"
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
