import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions
from . import get_containers_by_name


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestDagServerDeployment:
    def test_dag_server_statefulset_default(self, kube_version):
        """Test that no dag-server templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-server/dag-server-statefulset.yaml",
        )
        assert len(docs) == 0

    def test_dag_server_statefulset_dag_server_enabled(self, kube_version):
        """Test that a valid statefulset is rendered when dag-server is enabled."""
        values = {"dagServer": {"enabled": True}}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-server/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "StatefulSet"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-dag-server"
        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 1
        assert c_by_name["dag-server"]["command"] == [
            "sanic",
            "dag_deploy.server.app",
            "-H",
            "0.0.0.0",
        ]
        assert c_by_name["dag-server"]["image"].startswith(
            "quay.io/astronomer/ap-dag-server:"
        )
        assert c_by_name["dag-server"]["image"].startswith(
            "quay.io/astronomer/ap-dag-server:"
        )
        assert c_by_name["dag-server"]["livenessProbe"]

    def test_dag_server_statefulset_with_resource_overrides(self, kube_version):
        """Test that Dag Server statefulset are configurable with custom resource limits."""
        resources = {
            "requests": {"cpu": 99.5, "memory": "777Mi"},
            "limits": {"cpu": 99.6, "memory": "888Mi"},
        }
        values = {
            "dagServer": {
                "enabled": True,
                "resources": resources,
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-server/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "StatefulSet"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-dag-server"
        c_by_name = get_containers_by_name(doc)
        assert c_by_name["dag-server"]["resources"] == resources
        assert c_by_name["dag-server"]["resources"] == resources

    def test_dag_server_statefulset_with_securitycontext_overrides(self, kube_version):
        """Test that dag-server statefulset are configurable with custom securitycontext."""
        dag_serversecuritycontext = {"runAsUser": 12345, "privileged": True}
        values = {
            "dagServer": {"enabled": True, "securityContext": dag_serversecuritycontext}
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-server/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "StatefulSet"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-dag-server"
        assert (
            dag_serversecuritycontext
            == doc["spec"]["template"]["spec"]["securityContext"]
        )

    def test_dag_server_statefulset_with_custom_registry_secret(self, kube_version):
        """Test dag-server statefulset with custom registry secret."""
        values = {
            "airflow": {"registry": {"secretName": "gscsecret"}},
            "dagServer": {"enabled": True},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-server/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "StatefulSet"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-dag-server"
        assert [{"name": "gscsecret"}] == doc["spec"]["template"]["spec"][
            "imagePullSecrets"
        ]
