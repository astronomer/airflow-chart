import pytest

from tests import container_env_to_dict, git_root_dir, supported_k8s_versions
from tests.chart.helm_template_generator import render_chart

from . import get_containers_by_name


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayDeployment:
    def test_gsr_deployment_default(self, kube_version):
        """Test that no git-sync-relay templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only=[x.relative_to(git_root_dir) for x in (git_root_dir / "templates/git-sync-relay").glob("*")],
        )
        assert len(docs) == 0

    def test_gsr_deployment_gsr_mode_daemon(self, kube_version):
        """Test that a valid deployment is rendered when git-sync-relay is enabled with daemon mode."""
        values = {"gitSyncRelay": {"enabled": True}}

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
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
        assert c_by_name["git-daemon"]["image"].startswith("quay.io/astronomer/ap-git-daemon:")
        assert c_by_name["git-daemon"]["livenessProbe"]

    def test_gsr_deployment_gsr_mode_volume(self, kube_version):
        """Test that a valid deployment is rendered when git-sync-relay is enabled with default mode."""
        values = {"gitSyncRelay": {"enabled": True}}

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
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
        assert c_by_name["git-daemon"]["image"].startswith("quay.io/astronomer/ap-git-daemon:")
        assert c_by_name["git-daemon"]["livenessProbe"]

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
            {"name": "git-repo-contents", "emptyDir": {}},
            {
                "name": "git-secret",
                "secret": {"secretName": "a-custom-secret-name"},
            },
            {
                "name": "release-name-git-sync-config",
                "configMap": {"name": "release-name-git-sync-config"},
            },
        ]
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
        assert c_by_name["git-daemon"]["image"].startswith("quay.io/astronomer/ap-git-daemon:")
        assert c_by_name["git-sync"]["volumeMounts"] == [
            {
                "name": "git-secret",
                "mountPath": "/etc/git-secret/ssh",
                "readOnly": True,
                "subPath": "gitSshKey",
            },
            {
                "name": "release-name-git-sync-config",
                "mountPath": "/etc/git-secret/known_hosts",
                "readOnly": True,
                "subPath": "known_hosts",
            },
            {"name": "git-repo-contents", "mountPath": "/git"},
        ]
        assert container_env_to_dict(c_by_name["git-sync"]) == {
            "GIT_SYNC_ROOT": "/git",
            "GIT_SYNC_REPO": "not-the-default-url",
            "GIT_SYNC_BRANCH": "not-the-default-branch",
            "GIT_SYNC_DEPTH": "22",
            "GIT_SYNC_WAIT": "333",
            "GIT_SYNC_SSH": "true",
            "GIT_SSH_KEY_FILE": "/etc/git-secret/ssh",
            "GIT_KNOWN_HOSTS": "true",
            "GIT_SSH_KNOWN_HOSTS_FILE": "/etc/git-secret/known_hosts",
        }
        assert c_by_name["git-daemon"]["livenessProbe"]

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
            {"name": "git-repo-contents", "emptyDir": {}},
            {
                "name": "release-name-git-sync-config",
                "configMap": {"name": "release-name-git-sync-config"},
            },
        ]
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
        assert c_by_name["git-daemon"]["image"].startswith("quay.io/astronomer/ap-git-daemon:")
        assert c_by_name["git-sync"]["volumeMounts"] == [
            {"name": "git-repo-contents", "mountPath": "/git"},
        ]
        assert container_env_to_dict(c_by_name["git-sync"]) == {
            "GIT_SYNC_ROOT": "/git",
            "GIT_SYNC_REPO": "not-the-default-url",
            "GIT_SYNC_BRANCH": "not-the-default-branch",
            "GIT_SYNC_DEPTH": "22",
            "GIT_SYNC_WAIT": "333",
        }
        assert c_by_name["git-daemon"]["livenessProbe"]

    def test_gsr_deployment_with_resource_overrides(self, kube_version):
        """Test that gitsync relay deployment are configurable with custom resource limits."""
        resources = {
            "requests": {"cpu": 99.5, "memory": "777Mi"},
            "limits": {"cpu": 99.6, "memory": "888Mi"},
        }
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "gitSyncResources": resources,
                "gitDaemonResources": resources,
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
        gsrsecuritycontext = {"runAsUser": 12345, "privileged": True}
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
        assert gsrsecuritycontext == doc["spec"]["template"]["spec"]["securityContext"]

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

    def test_gsr_deployment_with_shared_volume(self, kube_version):
        """Test that a valid deployment is rendered when git-sync-relay is enabled."""
        values = {"gitSyncRelay": {"enabled": True, "mode": "shared_volume"}}

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
        c_by_name = get_containers_by_name(deployment)
        assert not c_by_name.get("git-daemon")
        assert len(c_by_name) == 1
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
