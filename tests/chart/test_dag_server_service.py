import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestDagServerService:
    def test_dag_server_service_default(self, kube_version):
        """Test that no dag-server service templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-service.yaml",
        )
        assert len(docs) == 0

    def test_dag_server_service_dag_server_enabled(self, kube_version):
        """Test that a valid service is rendered when dag-server is enabled."""
        values = {"dagDeploy": {"enabled": True}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-service.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Service"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "release-name-dag-server"
