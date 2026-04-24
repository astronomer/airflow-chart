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

    def test_init_job_uses_standard_git_sync_image(self, kube_version):
        """Test that the init job uses the standard ap-git-sync image, not the relay image."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        c_by_name = get_containers_by_name(doc)
        assert "quay.io/astronomer/ap-git-sync" in c_by_name["git-sync"]["image"]
        assert "ap-git-sync-relay" not in c_by_name["git-sync"]["image"]

        c_by_name_with_init = get_containers_by_name(doc, include_init_containers=True)
        assert "quay.io/astronomer/ap-git-sync" in c_by_name_with_init["git-config-manager"]["image"]

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

    def test_init_job_git_sync_one_time(self, kube_version):
        """Test that GIT_SYNC_ONE_TIME is set so the job terminates after one sync."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = _find_doc_by_kind(docs, "Job")

        c_by_name = get_containers_by_name(doc)
        assert "git-sync" in c_by_name
        env = get_env_vars_dict(c_by_name["git-sync"]["env"])
        assert env["GIT_SYNC_ONE_TIME"] == "true"
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
