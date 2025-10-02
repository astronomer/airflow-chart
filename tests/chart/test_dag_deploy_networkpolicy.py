import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestDagDeployNetworkPolicy:
    def test_dag_deploy_networkpolicy_default(self, kube_version):
        """Test that no dag-deploy templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-networkpolicy.yaml",
        )
        assert len(docs) == 0

    def test_gsr_networkpolicy_defaults_with_authsidecar_enabled(self, kube_version):
        """Test that a no networkPolicy are rendered when dag-deploy is enabled."""

        values = {
            "dagDeploy": {"enabled": True},
            "authSidecar": {"enabled": True},
            "platform": {"namespace": "test-ns-99", "release": "test-release-42"},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-networkpolicy.yaml",
            values=values,
        )
        assert len(docs) == 0

    @pytest.mark.parametrize(
        "plane_mode,ingress_name",
        [("control", "cp-ingress-controller"), ("data", "dp-ingress-controller"), ("unified", "cp-ingress-controller")],
    )
    def test_dag_deploy_networkpolicy_dag_deploy_enabled_with_dataplane_mode(self, plane_mode, ingress_name, kube_version):
        """Test that a valid networkPolicy is rendered when dag-deploy and networkPolicies are enabled."""

        values = {
            "airflow": {"networkPolicies": {"enabled": True}},
            "dagDeploy": {"enabled": True},
            "platform": {"namespace": "test-ns-99", "release": "test-release-42", "mode": plane_mode},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-networkpolicy.yaml",
            values=values,
        )
        assert len(docs) == 1
        spec = docs[0]["spec"]

        assert {
            "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "test-ns-99"}},
            "podSelector": {
                "matchLabels": {
                    "tier": "nginx",
                    "component": ingress_name,
                    "release": "test-release-42",
                }
            },
        } == spec["ingress"][1]["from"][1]

    def test_dag_deploy_networkpolicy_dag_deploy_enabled(self, kube_version):
        """Test that a valid networkPolicy is rendered when dag-deploy and networkPolicies are enabled."""

        values = {
            "airflow": {"networkPolicies": {"enabled": True}},
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

        assert all(x["ports"] == [{"protocol": "TCP", "port": 8000}] for x in spec["ingress"])

        assert spec["ingress"][0]["from"] == [{"podSelector": {"matchLabels": {"release": "release-name", "tier": "airflow"}}}]

        assert len(spec["ingress"][1]["from"]) == 2

        assert {
            "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "test-ns-99"}},
            "podSelector": {
                "matchLabels": {
                    "app": "houston",
                    "component": "houston",
                    "release": "test-release-42",
                }
            },
        } == spec["ingress"][1]["from"][0]
        assert {
            "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "test-ns-99"}},
            "podSelector": {
                "matchLabels": {
                    "tier": "nginx",
                    "component": "cp-ingress-controller",
                    "release": "test-release-42",
                }
            },
        } == spec["ingress"][1]["from"][1]

        assert [{"protocol": "TCP", "port": 8000}] == spec["ingress"][1]["ports"]

    def test_dag_deploy_networkpolicy_with_authsidecar_enabled(self, kube_version):
        """Test that a valid networkPolicy are rendered when dag-deploy is enabled."""

        values = {
            "airflow": {"networkPolicies": {"enabled": True}},
            "dagDeploy": {"enabled": True},
            "authSidecar": {"enabled": True},
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

        assert spec["ingress"][0]["from"] == [{"podSelector": {"matchLabels": {"release": "release-name", "tier": "airflow"}}}]

        assert len(spec["ingress"][1]["from"]) == 2

        assert {
            "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "test-ns-99"}},
            "podSelector": {
                "matchLabels": {
                    "app": "houston",
                    "component": "houston",
                    "release": "test-release-42",
                }
            },
        } == spec["ingress"][1]["from"][0]

        assert {"namespaceSelector": {"matchLabels": {"network.openshift.io/policy-group": "ingress"}}} == spec["ingress"][1][
            "from"
        ][1]

        assert [
            {"protocol": "TCP", "port": 8000},
            {"protocol": "TCP", "port": 8084},
        ] == spec["ingress"][1]["ports"]

    def test_dag_deploy_networkpolicy_with_authsidecar_and_ingress_allowed_namespaces_enabled(self, kube_version):
        """Test that a valid networkPolicy are rendered when authsidecar is enabled and ingressAllowedNamespaces is enabled."""

        values = {
            "airflow": {"networkPolicies": {"enabled": True}},
            "dagDeploy": {"enabled": True},
            "authSidecar": {"enabled": True, "ingressAllowedNamespaces": ["astro", "ingress-namespace"]},
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

        assert spec["ingress"][0]["from"] == [{"podSelector": {"matchLabels": {"release": "release-name", "tier": "airflow"}}}]

        assert len(spec["ingress"][1]["from"]) == 3

        assert {
            "namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "test-ns-99"}},
            "podSelector": {
                "matchLabels": {
                    "app": "houston",
                    "component": "houston",
                    "release": "test-release-42",
                }
            },
        } == spec["ingress"][1]["from"][0]

        assert {"namespaceSelector": {"matchLabels": {"network.openshift.io/policy-group": "ingress"}}} == spec["ingress"][1][
            "from"
        ][1]

        assert {
            "namespaceSelector": {
                "matchExpressions": [
                    {"key": "kubernetes.io/metadata.name", "operator": "In", "values": ["astro", "ingress-namespace"]}
                ]
            }
        } == spec["ingress"][1]["from"][2]

        assert [
            {"protocol": "TCP", "port": 8000},
            {"protocol": "TCP", "port": 8084},
        ] == spec["ingress"][1]["ports"]
