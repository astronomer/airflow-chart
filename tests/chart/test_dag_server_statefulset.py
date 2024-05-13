import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions
from . import get_containers_by_name


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestDagServerStatefulSet:
    def test_dag_server_statefulset_default(self, kube_version):
        """Test that no dag-server templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
        )
        assert len(docs) == 0

    def test_dag_server_statefulset_dag_server_enabled(self, kube_version):
        """Test that a valid statefulset is rendered when dag-server is enabled."""
        values = {"dagDeploy": {"enabled": True}}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
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
            "quay.io/astronomer/ap-dag-deploy:"
        )
        assert c_by_name["dag-server"]["image"].startswith(
            "quay.io/astronomer/ap-dag-deploy:"
        )
        assert c_by_name["dag-server"]["livenessProbe"]

    def test_dag_server_statefulset_with_resource_overrides(self, kube_version):
        """Test that Dag Server statefulset are configurable with custom resource limits."""
        resources = {
            "requests": {"cpu": 99.9, "memory": "777Mi"},
            "limits": {"cpu": 66.6, "memory": "888Mi"},
        }
        values = {
            "dagDeploy": {
                "enabled": True,
                "resources": resources,
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "StatefulSet"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-dag-server"
        c_by_name = get_containers_by_name(doc)
        assert c_by_name["dag-server"]["resources"] == resources

    def test_dag_server_statefulset_with_podsecuritycontext_overrides(
        self, kube_version
    ):
        """Test that dag-server statefulset are configurable with custom securitycontext."""
        dag_server_pod_securitycontext = {"runAsUser": 12345, "privileged": True}
        dag_server_container_securitycontext = {"allowPrivilegeEscalation": False}
        values = {
            "dagDeploy": {
                "enabled": True,
                "podSecurityContext": dag_server_pod_securitycontext,
                "containerSecurityContext": dag_server_container_securitycontext,
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "StatefulSet"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-dag-server"
        assert (
            dag_server_pod_securitycontext
            == doc["spec"]["template"]["spec"]["securityContext"]
        )
        assert (
            dag_server_container_securitycontext
            == doc["spec"]["template"]["spec"]["containers"][0]["securityContext"]
        )

    def test_dag_server_statefulset_with_custom_registry_secret(self, kube_version):
        """Test dag-server statefulset with custom registry secret."""
        values = {
            "airflow": {"registry": {"secretName": "gscsecret"}},
            "dagDeploy": {"enabled": True},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
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
