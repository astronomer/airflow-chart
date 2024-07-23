import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions
from . import get_containers_by_name


def common_default_tests(doc):
    """Test cases for default dag-server sts enabled"""

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

        common_default_tests(doc)

        c_by_name = get_containers_by_name(doc)

        env_vars = {x["name"]: x["value"] for x in c_by_name["dag-server"]["env"]}
        assert (
            env_vars["HOUSTON_SERVICE_ENDPOINT"]
            == "http://-houston..svc.cluster.local.:8871/v1/"
        )

        assert "persistentVolumeClaimRetentionPolicy" not in doc["spec"]

    def test_dag_server_statefulset_houston_service_endpoint_override(
        self, kube_version
    ):
        """Test that we see the right HOUSTON_SERVICE_ENDPOINT value when the relevant variables are set."""
        values = {
            "dagDeploy": {"enabled": True},
            "platform": {"release": "test-release", "namespace": "test-namespace"},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        common_default_tests(doc)

        c_by_name = get_containers_by_name(doc)

        env_vars = {x["name"]: x["value"] for x in c_by_name["dag-server"]["env"]}
        assert (
            env_vars["HOUSTON_SERVICE_ENDPOINT"]
            == "http://test-release-houston.test-namespace.svc.cluster.local.:8871/v1/"
        )

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

        common_default_tests(doc)

        c_by_name = get_containers_by_name(doc)
        assert c_by_name["dag-server"]["resources"] == resources

    def test_dag_server_statefulset_with_securitycontext_overrides(self, kube_version):
        """Test that dag-server statefulset are configurable with custom securitycontext."""
        dag_serversecuritycontext = {"runAsUser": 12345, "privileged": True}
        values = {
            "dagDeploy": {"enabled": True, "securityContext": dag_serversecuritycontext}
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        common_default_tests(doc)

        assert (
            dag_serversecuritycontext
            == doc["spec"]["template"]["spec"]["securityContext"]
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

        common_default_tests(doc)

        assert [{"name": "gscsecret"}] == doc["spec"]["template"]["spec"][
            "imagePullSecrets"
        ]

    def test_dag_server_statefulset_with_persistentVolumeClaimRetentionPolicy_overrides(
        self, kube_version
    ):
        """Test that dag-server statefulset are configurable with persistentVolumeClaimRetentionPolicy."""
        persistentVolumeClaimRetentionPolicy = {
                "persistentVolumeClaimRetentionPolicy": {
                    "whenDeleted": "Retain",
                    "whenScaled": "Delete",
                }
            }
        values = {
            "dagDeploy": {
                "enabled": True,
                "persistence": {
                "persistentVolumeClaimRetentionPolicy": persistentVolumeClaimRetentionPolicy,}
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        common_default_tests(doc)

        assert (
            persistentVolumeClaimRetentionPolicy
            == doc["spec"]["persistentVolumeClaimRetentionPolicy"]
        )
