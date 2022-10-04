import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayConfigmap:
    def test_gsr_configmap_default(self, kube_version):
        """Test that no git-sync-relay templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-configmap.yaml",
        )
        assert len(docs) == 0

    def test_gsr_configmap_gsr_enabled(self, kube_version):
        """Test that valid configmaps are rendered when git-sync-relay is enabled."""
        values = {"gitSyncRelay": {"enabled": True}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-configmap.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        expected_result = {
            "apiVersion": "v1",
            "data": {
                "known_hosts": "github.com ssh-ed25519 "
                "AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl\n"
                "gitlab.com ssh-ed25519 "
                "AAAAC3NzaC1lZDI1NTE5AAAAIAfuCHKVTjquxvt6CM6tdG4SLp1Btn/nOeHHE5UOzRdf\n"
            },
            "kind": "ConfigMap",
            "metadata": {
                "labels": {
                    "chart": "release-name-1.1.0-rc1",
                    "component": "release-name-git-sync-relay",
                    "heritage": "Helm",
                    "release": "release-name",
                    "tier": "airflow",
                },
                "name": "release-name-git-sync-config",
            },
        }

        expected_result["metadata"]["labels"].pop("chart")
        doc["metadata"]["labels"].pop("chart")

        assert doc == expected_result

    def test_gsr_configmap_gsr_enabled_with_custom_known_hosts(self, kube_version):
        """Test that valid configmaps are rendered when git-sync-relay is enabled and has custom knownHosts."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "knownHosts": "not-the-default-knownHosts",
                },
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-configmap.yaml",
            values=values,
        )
        assert len(docs) == 1
        assert docs[0]["data"] == {"known_hosts": "not-the-default-knownHosts\n"}
