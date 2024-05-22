import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayNetworkPolicy:
    def test_gsr_networkpolicy_default(self, kube_version):
        """Test that no git-sync-relay templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-networkpolicy.yaml",
        )
        assert len(docs) == 0

    def test_gsr_networkpolicy_gsr_enabled(self, kube_version):
        """Test that a valid networkPolicy are rendered when git-sync-relay is enabled."""
        values = {"gitSyncRelay": {"enabled": True}}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-networkpolicy.yaml",
            values=values,
        )
        assert len(docs) == 1
