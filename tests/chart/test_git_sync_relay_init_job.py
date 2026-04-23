import pytest

from tests import supported_k8s_versions
from tests.utils import get_containers_by_name, get_env_vars_dict
from tests.utils.chart import render_chart

show_only = "templates/git-sync-relay/git-sync-relay-init-job.yaml"


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
        assert len(docs) == 1
        doc = docs[0]

        assert doc["kind"] == "Job"
        assert doc["apiVersion"] == "batch/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay-init"
        assert doc["metadata"]["annotations"]["helm.sh/hook"] == "pre-install,pre-upgrade"
        assert doc["metadata"]["annotations"]["helm.sh/hook-delete-policy"] == "before-hook-creation"
        assert doc["metadata"]["annotations"]["helm.sh/hook-weight"] == "5"

    def test_init_job_spec_defaults(self, kube_version):
        """Test Job spec has backoffLimit, activeDeadlineSeconds, and correct pod spec."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = docs[0]

        assert doc["spec"]["backoffLimit"] == 3
        assert doc["spec"]["activeDeadlineSeconds"] == 300
        assert doc["spec"]["template"]["spec"]["restartPolicy"] == "Never"

    def test_init_job_has_git_config_manager_init_container(self, kube_version):
        """Test that the init job includes the git-config-manager initContainer."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = docs[0]

        c_by_name = get_containers_by_name(doc, include_init_containers=True)
        assert "git-config-manager" in c_by_name
        assert c_by_name["git-config-manager"]["command"] == [
            "git", "config", "--global", "--add", "safe.directory", "/git",
        ]
        volume_mounts = c_by_name["git-config-manager"]["volumeMounts"]
        mount_names = [m["name"] for m in volume_mounts]
        assert "git-sync-home" in mount_names

    def test_init_job_git_sync_one_time(self, kube_version):
        """Test that GIT_SYNC_ONE_TIME is set so the job terminates after one sync."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = docs[0]

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
        doc = docs[0]

        volumes = doc["spec"]["template"]["spec"]["volumes"]
        volume_names = [v["name"] for v in volumes]
        assert "git-sync-home" in volume_names
        assert "git-repo-contents" in volume_names
        assert "release-name-git-sync-config" in volume_names
        assert "config-volume" not in volume_names
        assert "sidecar-logging-consumer" not in volume_names
        assert "nginx-sidecar-conf" not in volume_names

        pvc_vol = next(v for v in volumes if v["name"] == "git-repo-contents")
        assert pvc_vol["persistentVolumeClaim"]["claimName"] == "git-repo-contents"

    def test_init_job_git_sync_home_volume_mount(self, kube_version):
        """Test that the git-sync container mounts git-sync-home."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = docs[0]

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
                "repo": {"sshPrivateKeySecretName": "my-ssh-secret"},
            }
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = docs[0]

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
        doc = docs[0]

        c_by_name = get_containers_by_name(doc)
        env = get_env_vars_dict(c_by_name["git-sync"]["env"])
        assert env["GIT_KNOWN_HOSTS"] == "true"
        assert env["GIT_SSH_KNOWN_HOSTS_FILE"] == "/etc/git-secret/known_hosts"

    def test_init_job_does_not_include_unnecessary_env_vars(self, kube_version):
        """Test that webhook/wait/fetch-mode env vars are not in the init job."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "repoFetchMode": "webhook",
                "webhookSecretKey": "my-secret",
            }
        }
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = docs[0]

        c_by_name = get_containers_by_name(doc)
        env = get_env_vars_dict(c_by_name["git-sync"]["env"])
        assert "GIT_SYNC_REPO_FETCH_MODE" not in env
        assert "GIT_SYNC_WEBHOOK_SECRET" not in env
        assert "GIT_SYNC_WAIT" not in env

    def test_init_job_no_probes(self, kube_version):
        """Test that the init job container has no liveness/readiness probes."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = docs[0]

        c_by_name = get_containers_by_name(doc)
        assert "livenessProbe" not in c_by_name["git-sync"]
        assert "readinessProbe" not in c_by_name["git-sync"]

    def test_init_job_uses_service_account_template(self, kube_version):
        """Test that the init job uses the gitSyncRelay serviceAccountName template."""
        values = {"gitSyncRelay": {"enabled": True, "repoShareMode": "shared_volume"}}
        docs = render_chart(kube_version=kube_version, show_only=show_only, values=values)
        doc = docs[0]

        sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert sa_name == "release-name-git-sync-relay"
