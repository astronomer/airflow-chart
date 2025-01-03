import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


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
        assert doc["metadata"]["name"] == "release-name-dag-server"

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
            show_only=["templates/dag-deploy/dag-server-serviceaccount.yaml", "templates/dag-deploy/dag-server-statefulset.yaml"],
            values=values,
        )
        assert len(docs) == 2
        doc = docs[0]
        assert doc["kind"] == "ServiceAccount"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "release-name-dag-server"
        assert doc["metadata"]["annotations"] == annotations
        assert "release-name-dag-server" == docs[1]["spec"]["template"]["spec"]["serviceAccountName"]

    def test_dag_server_serviceaccount_overrides_defaults(self, kube_version):
        """Test that a serviceAccount overridable with disabled creation"""
        values = {
            "dagDeploy": {
                "enabled": True,
                "serviceAccount": {"create": False},
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only=["templates/dag-deploy/dag-server-serviceaccount.yaml", "templates/dag-deploy/dag-server-statefulset.yaml"],
            values=values,
        )
        assert len(docs) == 1
        assert "default" == docs[0]["spec"]["template"]["spec"]["serviceAccountName"]

    def test_dag_server_serviceaccount_overrides(self, kube_version):
        """Test that a serviceAccount overridable with disabled creation"""
        values = {
            "dagDeploy": {
                "enabled": True,
                "serviceAccount": {"create": False, "name": "dag-server"},
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only=["templates/dag-deploy/dag-server-serviceaccount.yaml", "templates/dag-deploy/dag-server-statefulset.yaml"],
            values=values,
        )
        assert len(docs) == 1
        assert "dag-server" == docs[0]["spec"]["template"]["spec"]["serviceAccountName"]
