import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


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

        values = {
            "gitSyncRelay": {"enabled": True},
            "platform": {"namespace": "test-ns-99", "release": "test-release-42"},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-networkpolicy.yaml",
            values=values,
        )
        assert len(docs) == 1
        spec = docs[0]["spec"]

        assert list(spec["podSelector"].keys()) == ["matchLabels"]
        assert spec["policyTypes"] == ["Ingress"]
        assert spec["podSelector"]["matchLabels"] == {"tier": "airflow", "component": "git-sync-relay", "release": "release-name"}

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
                    "component": "ingress-controller",
                    "release": "test-release-42",
                }
            },
        } == spec["ingress"][1]["from"][1]

        assert [{"protocol": "TCP", "port": 8000}] == spec["ingress"][1]["ports"]

    def test_gsr_networkpolicy_with_authsidecar_enabled(self, kube_version):
        """Test that a valid networkPolicy are rendered when git-sync-relay is enabled."""

        values = {
            "gitSyncRelay": {"enabled": True},
            "authSidecar": {"enabled": True},
            "platform": {"namespace": "test-ns-99", "release": "test-release-42"},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-networkpolicy.yaml",
            values=values,
        )
        assert len(docs) == 1
        spec = docs[0]["spec"]

        assert list(spec["podSelector"].keys()) == ["matchLabels"]
        assert spec["policyTypes"] == ["Ingress"]
        assert spec["podSelector"]["matchLabels"] == {"tier": "airflow", "component": "git-sync-relay", "release": "release-name"}

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
