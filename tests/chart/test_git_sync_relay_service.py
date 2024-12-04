import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayService:
    def test_gsr_service_default(self, kube_version):
        """Test that no git-sync-relay templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-service.yaml",
        )
        assert len(docs) == 0

    def test_gsr_service_gsr_enabled(self, kube_version):
        """Test that a valid service is rendered when git-sync-relay is enabled."""
        values = {"gitSyncRelay": {"enabled": True}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-service.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Service"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
