import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestDagServerRoleBinding:
    def test_dag_deploy_rolebinding_default(self, kube_version):
        """Test that no dag-server RoleBinding templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-rolebinding.yaml",
        )
        assert len(docs) == 0

    def test_dag_deploy_rolebinding_dag_server_enabled(self, kube_version):
        """Test that a valid RoleBinding is rendered when dag-server is enabled."""
        values = {"dagServer": {"enabled": True}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-rolebinding.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "RoleBinding"
        assert doc["apiVersion"] == "rbac.authorization.k8s.io/v1"
        assert doc["metadata"]["name"] == "release-name-dag-deploy-role-binding"
