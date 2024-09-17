import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestDagServerServiceAccount:
    def test_dag_server_service_default(self, kube_version):
        """Test that no dag-server service templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-serviceaccount.yaml",
        )
        assert len(docs) == 0

    def test_dag_server_service_dag_server_enabled(self, kube_version):
        """Test that a valid serviceAccount is rendered when dag-server is enabled."""
        values = {"dagDeploy": {"enabled": True}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-serviceaccount.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "ServiceAccount"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "release-name-airflow-dag-server"

    def test_dag_server_service_dag_server_annotations(self, kube_version):
        """Test that a valid serviceAccount is rendered with proper annotations
        when dag-server is enabled and annotations are provided."""
        annotations = {"foo-key": "foo-value", "bar-key": "bar-value"}
        values = {
            "dagDeploy": {
                "enabled": True,
                "serviceAccount": {"annotations": annotations},
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-serviceaccount.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "ServiceAccount"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "release-name-airflow-dag-server"
        assert doc["metadata"]["annotations"] == annotations
