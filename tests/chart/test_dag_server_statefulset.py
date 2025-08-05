import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart

from . import get_containers_by_name

readinessProbe = {"httpGet": {"initialDelaySeconds": 20, "periodSeconds": 20, "path": "/rhealthz", "port": 8080, "scheme": "HTTP"}}
livenessProbe = {"httpGet": {"initialDelaySeconds": 20, "periodSeconds": 20, "path": "/chealthz", "port": 8080, "scheme": "HTTP"}}
resources = {
    "requests": {"cpu": 99.9, "memory": "777Mi"},
    "limits": {"cpu": 66.6, "memory": "888Mi"},
}


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
    assert c_by_name["dag-server"]["image"].startswith("quay.io/astronomer/ap-dag-deploy:")
    assert c_by_name["dag-server"]["image"].startswith("quay.io/astronomer/ap-dag-deploy:")
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
        assert env_vars["HOUSTON_SERVICE_ENDPOINT"] == "http://-houston..svc.cluster.local.:8871/v1/"

        assert "persistentVolumeClaimRetentionPolicy" not in doc["spec"]

    def test_dag_server_statefulset_houston_service_endpoint_override(self, kube_version):
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
        assert env_vars["HOUSTON_SERVICE_ENDPOINT"] == "http://test-release-houston.test-namespace.svc.cluster.local.:8871/v1/"

    def test_dag_server_statefulset_with_resource_overrides(self, kube_version):
        """Test that Dag Server statefulset are configurable with custom resource limits."""
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
        dag_server_pod_securitycontext = {
            "runAsUser": 12345,
            "allowPrivilegeEscalation": True,
            "runAsGroup": 1000,
            "fsGroup": 2000,
            "readOnlyRootFilesystem": True,
        }
        dag_server_container_securitycontext = {"allowPrivilegeEscalation": False}
        values = {
            "dagDeploy": {
                "enabled": True,
                "securityContexts": {
                    "pod": dag_server_pod_securitycontext,
                    "container": dag_server_container_securitycontext,
                },
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
        spec = doc["spec"]["template"]["spec"]
        assert dag_server_pod_securitycontext == spec["securityContext"]
        assert dag_server_container_securitycontext == spec["containers"][0]["securityContext"]

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

        assert [{"name": "gscsecret"}] == doc["spec"]["template"]["spec"]["imagePullSecrets"]

    def test_dag_server_statefulset_with_persistentVolumeClaimRetentionPolicy_overrides(self, kube_version):
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
                    "persistentVolumeClaimRetentionPolicy": persistentVolumeClaimRetentionPolicy,
                },
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

        assert persistentVolumeClaimRetentionPolicy == doc["spec"]["persistentVolumeClaimRetentionPolicy"]

    def test_dag_server_statefulset_with_sidecar_enabled(self, kube_version):
        """Test dag-server statefulset with logging sidecar enabled."""
        values = {"dagDeploy": {"enabled": True}, "loggingSidecar": {"enabled": True, "resources": resources}}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 2
        assert "sidecar-log-consumer" in c_by_name
        assert c_by_name["sidecar-log-consumer"]["resources"] == resources

    def test_dag_server_statefulset_with_sidecar_enabled_with_resource_overrides(self, kube_version):
        """Test dag-server statefulset with logging sidecar resource overrides."""
        values = {"dagDeploy": {"enabled": True}, "loggingSidecar": {"enabled": True}}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 2
        assert c_by_name["dag-server"]["command"] == ["bash"]
        c_by_name["dag-server"]["args"] == [
            "-c",
            "sanic dag_deploy.server.app -H 0.0.0.0 1> >( tee -a /var/log/sidecar-logging-consumer/out.log ) 2> >( tee -a /var/log/sidecar-logging-consumer/err.log >&2 )",
        ]
        assert "sidecar-log-consumer" in c_by_name

    def test_dag_server_statefulset_with_sidecar_and_authproxy_enabled(self, kube_version):
        """Test dag-server statefulset with custom registry secret."""
        values = {
            "dagDeploy": {"enabled": True},
            "loggingSidecar": {"enabled": True},
            "authSidecar": {"enabled": True},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 3
        assert "dag-server" in c_by_name
        assert "auth-proxy" in c_by_name
        assert c_by_name["dag-server"]["command"] == ["bash"]
        c_by_name["dag-server"]["args"] == [
            "-c",
            "sanic dag_deploy.server.app -H 0.0.0.0 1> >( tee -a /var/log/sidecar-logging-consumer/out.log ) 2> >( tee -a /var/log/sidecar-logging-consumer/err.log >&2 )",
        ]
        assert "sidecar-log-consumer" in c_by_name

    def test_dag_server_statefulset_liveness_and_readiness_probes_with_dag_server_enabled(self, kube_version):
        """Test that a valid statefulset is rendered when dag-server is enabled with readiness and liveness probes."""
        values = {"dagDeploy": {"enabled": True, "readinessProbe": readinessProbe, "livenessProbe": livenessProbe}}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        common_default_tests(doc)

        c_by_name = get_containers_by_name(doc)
        assert readinessProbe == c_by_name["dag-server"]["readinessProbe"]
        assert livenessProbe == c_by_name["dag-server"]["livenessProbe"]

    def test_dag_server_statefulset_with_probes_and_authproxy_enabled(self, kube_version):
        """Test that a valid statefulset is rendered when dag-server and authsidecar is enabled with readiness and liveness probes."""
        values = {
            "dagDeploy": {"enabled": True},
            "authSidecar": {"enabled": True, "readinessProbe": readinessProbe, "livenessProbe": livenessProbe},
            "loggingSidecar": {"enabled": True, "readinessProbe": readinessProbe, "livenessProbe": livenessProbe},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 3
        assert "dag-server" in c_by_name
        assert "auth-proxy" in c_by_name
        assert "sidecar-log-consumer" in c_by_name
        assert readinessProbe == c_by_name["auth-proxy"]["readinessProbe"]
        assert livenessProbe == c_by_name["auth-proxy"]["livenessProbe"]
        assert readinessProbe == c_by_name["sidecar-log-consumer"]["readinessProbe"]
        assert livenessProbe == c_by_name["sidecar-log-consumer"]["livenessProbe"]

    def test_dag_server_service_account_with_template(self, kube_version):
        """Test dag-server service account with template."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "dagDeploy": {
                    "enabled": True,
                    "serviceAccount": {
                        "create": False,
                        "name": "custom-{{ .Release.Name }}-dag-processor",
                    },
                },
            },
            show_only=["templates/dag-deploy/dag-server-statefulset.yaml", "templates/dag-deploy/dag-server-serviceaccount.yaml"],
        )
        assert len(docs) == 1
        service_accounts = [sa for sa in docs if sa.get("kind") == "ServiceAccount"]
        assert len(service_accounts) == 0
        doc = docs[0]
        assert doc["kind"] == "StatefulSet"
        assert doc["metadata"]["name"] == "release-name-dag-server"

    def test_dag_server_affinity(self, kube_version):
        """Test that dagserver affinity correctly inserts the affinity."""
        affinity = {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "foo",
                                    "operator": "In",
                                    "values": ["bar", "baz"],
                                }
                            ]
                        }
                    ]
                }
            }
        }
        values = {"dagDeploy": {"enabled": True,
                                "affinity": affinity }}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/dag-deploy/dag-server-statefulset.yaml",
            values=values,
        )
        doc = docs[0]
        common_default_tests(doc)
        assert len(docs) == 1
        assert docs[0]["spec"]["template"]["spec"]["affinity"] == affinity
