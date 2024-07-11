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

        values = {
            "dagDeploy": {"enabled": True},
            "platform": {"namespace": "test-ns-99", "release": "test-release-42"},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-networkpolicy.yaml",
            values=values,
        )
        assert len(docs) == 1
        spec = docs[0]["spec"]

        assert list(spec["podSelector"].keys()) == ["matchLabels"]
        assert spec["policyTypes"] == ["Ingress"]
        assert spec["podSelector"]["matchLabels"] == {
            "tier": "airflow",
            "component": "dag-server",
            "release": "release-name",
        }

        assert all(
            [x["ports"] == [{"protocol": "TCP", "port": 8000}] for x in spec["ingress"]]
        )

        assert spec["ingress"][0]["from"] == [
            {
                "podSelector": {
                    "matchLabels": {"release": "release-name", "tier": "airflow"}
                }
            }
        ]

        assert len(spec["ingress"][1]["from"]) == 1
        assert (
            spec["ingress"][1]["from"][0]["namespaceSelector"]["matchLabels"][
                "kubernetes.io/metadata.name"
            ]
            == "test-ns-99"
        )
        assert spec["ingress"][1]["from"][0]["podSelector"]["matchLabels"] == {
            "app": "houston",
            "component": "houston",
            "release": "test-release-42",
        }
