import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


def common_dag_downloader_rbac_tests(docs):
    """Test common asserts for dog downloader rbac."""
    assert len(docs) == 2
    for doc in docs:
        assert doc["kind"] == "RoleBinding"
        assert doc["apiVersion"] == "rbac.authorization.k8s.io/v1"
    server = docs[0]

    assert server["metadata"]["name"] == "release-name-dag-server-rolebinding"
    assert len(server["subjects"]) == 1
    assert server["subjects"][0]["kind"] == "ServiceAccount"
    assert server["subjects"][0]["name"] == "release-name-dag-server"
    assert server["subjects"][0]["namespace"] == "test-namespace"
    assert server["roleRef"]["kind"] == "Role"
    assert server["roleRef"]["name"] == "release-name-dag-server-role"
    assert server["roleRef"]["apiGroup"] == "rbac.authorization.k8s.io"


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
        values = {"dagDeploy": {"enabled": True}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-rolebinding.yaml",
            namespace="test-namespace",
            values=values,
        )
        common_dag_downloader_rbac_tests(docs)
        downloader = docs[1]
        assert downloader["metadata"]["name"] == "release-name-dag-downloader-rolebinding"
        assert len(downloader["subjects"]) == 4
        assert all(sub["kind"] == "ServiceAccount" for sub in downloader["subjects"])
        assert all(sub["namespace"] == "test-namespace" for sub in downloader["subjects"])
        assert downloader["roleRef"]["kind"] == "Role"
        assert downloader["roleRef"]["name"] == "release-name-dag-downloader-role"
        assert downloader["roleRef"]["apiGroup"] == "rbac.authorization.k8s.io"
        assert [
            {
                "kind": "ServiceAccount",
                "name": "release-name-airflow-webserver",
                "namespace": "test-namespace",
            },
            {
                "kind": "ServiceAccount",
                "name": "release-name-airflow-triggerer",
                "namespace": "test-namespace",
            },
            {
                "kind": "ServiceAccount",
                "name": "release-name-airflow-worker",
                "namespace": "test-namespace",
            },
            {
                "kind": "ServiceAccount",
                "name": "release-name-airflow-scheduler",
                "namespace": "test-namespace",
            },
        ] == downloader["subjects"]

    def test_dag_deploy_rolebinding_dag_server_enabled_with_dag_processor(self, kube_version):
        """Test that a valid RoleBinding is rendered when dag-server is enabled."""
        values = {"dagDeploy": {"enabled": True}, "airflow": {"dagProcessor": {"enabled": True}}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-deploy-rolebinding.yaml",
            namespace="test-namespace",
            values=values,
        )
        common_dag_downloader_rbac_tests(docs)
        downloader = docs[1]

        assert downloader["metadata"]["name"] == "release-name-dag-downloader-rolebinding"
        assert len(downloader["subjects"]) == 5
        assert all(sub["kind"] == "ServiceAccount" for sub in downloader["subjects"])
        assert all(sub["namespace"] == "test-namespace" for sub in downloader["subjects"])
        assert downloader["roleRef"]["kind"] == "Role"
        assert downloader["roleRef"]["name"] == "release-name-dag-downloader-role"
        assert downloader["roleRef"]["apiGroup"] == "rbac.authorization.k8s.io"
        assert [
            {
                "kind": "ServiceAccount",
                "name": "release-name-airflow-webserver",
                "namespace": "test-namespace",
            },
            {
                "kind": "ServiceAccount",
                "name": "release-name-airflow-triggerer",
                "namespace": "test-namespace",
            },
            {
                "kind": "ServiceAccount",
                "name": "release-name-airflow-worker",
                "namespace": "test-namespace",
            },
            {
                "kind": "ServiceAccount",
                "name": "release-name-airflow-scheduler",
                "namespace": "test-namespace",
            },
            {"kind": "ServiceAccount", "name": "release-name-airflow-dag-processor", "namespace": "test-namespace"},
        ] == downloader["subjects"]
