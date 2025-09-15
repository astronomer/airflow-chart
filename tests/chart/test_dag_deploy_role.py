import pytest

from tests import supported_k8s_versions
from tests.utils.chart import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestDagServerRole:
    def test_dag_server_role_default(self, kube_version):
        """Test that no dag-server Role templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-role.yaml",
        )
        assert len(docs) == 0

    def test_dag_server_role_dag_server_enabled(self, kube_version):
        """Test that a valid Role is rendered when dag-server is enabled."""
        values = {"dagDeploy": {"enabled": True}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-role.yaml",
            values=values,
        )
        assert len(docs) == 2
        for doc in docs:
            assert doc["kind"] == "Role"
            assert doc["apiVersion"] == "rbac.authorization.k8s.io/v1"
            assert doc["rules"][0]["apiGroups"] == [""]
            assert doc["rules"][0]["resources"] == ["configmaps"]

        server = docs[0]
        downloader = docs[1]

        assert server["metadata"]["name"] == "release-name-dag-server-role"
        assert len(server["rules"]) == 1
        assert server["rules"][0]["verbs"] == [
            "create",
            "get",
            "list",
            "patch",
            "update",
            "watch",
        ]

        assert downloader["metadata"]["name"] == "release-name-dag-downloader-role"
        assert len(downloader["rules"]) == 1
        assert downloader["rules"][0]["verbs"] == ["get", "list", "watch"]
