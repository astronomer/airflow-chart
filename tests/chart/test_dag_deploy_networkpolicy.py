import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestDagDeployNetworkPolicy:
    def test_dag_deploy_networkpolicy_default(self, kube_version):
        """Test that no dag-deploy templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-networkpolicy.yaml",
        )
        assert len(docs) == 0

    def test_dag_deploy_networkpolicy_dag_deploy_enabled(self, kube_version):
        """Test that a valid networkPolicy are rendered when dag-deploy is enabled."""

        values = {"dagDeploy": {"enabled": True}}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-networkpolicy.yaml",
            values=values,
        )
        assert len(docs) == 1
