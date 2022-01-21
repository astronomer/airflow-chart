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
        assert doc["kind"] == "ConfigMap"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "RELEASE-NAME-git-sync-config"
