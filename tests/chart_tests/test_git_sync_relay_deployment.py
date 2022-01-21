import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayDeployment:
    def test_gsr_deployment_default(self, kube_version):
        """Test that no git-sync-relay templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
        )
        assert len(docs) == 0

    def test_gsr_deployment_gsr_enabled(self, kube_version):
        """Test that a valid deployment is rendered when git-sync-relay is enabled."""
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
        assert doc["metadata"]["name"] == "RELEASE-NAME-git-sync-relay"
        c_by_name = {
            c["name"]: c for c in doc["spec"]["template"]["spec"]["containers"]
        }
        assert len(c_by_name) == 2
        assert c_by_name["git-sync"]["image"].startswith(
            "quay.io/astronomer/ap-git-sync:"
        )
        assert c_by_name["git-daemon"]["image"].startswith(
            "quay.io/astronomer/ap-git-daemon:"
        )

    def test_gsr_deployment_with_ssh_credentials_and_known_hosts(self, kube_version):
        """Test that a valid deployment is rendered when enabling git-sync with ssh credentials and known hosts and other custom configs."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "git@github.com:astronomer/astronomer.git",
                    "branch": "git-sync-test",
                    "depth": 1,
                    "wait": 60,
                    "subPath": "dags",
                    "sshPrivateKeySecretName": "git-sync-ssh-key",
                    "knownHosts": "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl\ngitlab.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAfuCHKVTjquxvt6CM6tdG4SLp1Btn/nOeHHE5UOzRdf\n",
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
        assert doc["metadata"]["name"] == "RELEASE-NAME-git-sync-relay"
        c_by_name = {
            c["name"]: c for c in doc["spec"]["template"]["spec"]["containers"]
        }
        assert len(c_by_name) == 2
        assert c_by_name["git-sync"]["image"].startswith(
            "quay.io/astronomer/ap-git-sync:"
        )
        assert c_by_name["git-daemon"]["image"].startswith(
            "quay.io/astronomer/ap-git-daemon:"
        )
