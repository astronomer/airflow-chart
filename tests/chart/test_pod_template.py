import pytest
import yaml

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


def common_pod_template_test(docs):
    """Test common asserts for pod template pod spec."""
    assert len(docs) == 1
    doc = docs[0]
    assert doc["kind"] == "ConfigMap"


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestPodTemplate:
    def test_pod_template_defaults(self, kube_version):
        """Test airflow pod template defaults."""
        docs = render_chart(
            kube_version=kube_version,
            values={},
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert {"tier": "airflow", "component": "worker", "release": "release-name"} == podTemplate["metadata"]["labels"]
        assert "runtimeClassName" not in podTemplate["spec"]
        assert "priorityClassName" not in podTemplate["spec"]
        assert podTemplate["spec"]["nodeSelector"] == {}
        assert podTemplate["spec"]["affinity"] == {}
        assert podTemplate["spec"]["tolerations"] == []

    def test_pod_template_labels_overrides(self, kube_version):
        """Test airflow pod template labels overrides."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "labels": {"service": "airflow"},
                    "workers": {"labels": {"servicetype": "workers"}},
                }
            },
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert {
            "tier": "airflow",
            "component": "worker",
            "release": "release-name",
            "service": "airflow",
            "servicetype": "workers",
        } == podTemplate["metadata"]["labels"]

    def test_pod_template_pod_annotation_defaults(self, kube_version):
        """Test airflow pod template labels overrides."""
        docs = render_chart(
            kube_version=kube_version,
            values={},
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert "annotations" not in podTemplate["metadata"]

    def test_pod_template_pod_annotation_overrides(self, kube_version):
        """Test airflow pod template labels overrides."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "airflowPodAnnotations": {"app.kubernetes.io": "airflow"},
                    "workers": {"podAnnotations": {"app.worker.kubernetes.io": "workers"}},
                }
            },
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert {"app.kubernetes.io": "airflow", "app.worker.kubernetes.io": "workers"} == podTemplate["metadata"]["annotations"]

    def test_pod_template_pod_priority_class_name_overrides(self, kube_version):
        """Test airflow pod template labels overrides."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "workers": {"priorityClassName": "criticalworkload"},
                }
            },
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert "criticalworkload" == podTemplate["spec"]["priorityClassName"]

    def test_pod_template_pod_runtime_class_name_overrides(self, kube_version):
        """Test airflow pod template labels overrides."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "workers": {"runtimeClassName": "criticalworkload"},
                }
            },
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert "criticalworkload" == podTemplate["spec"]["runtimeClassName"]

    def test_pod_template_worker_env_overrides(self, kube_version):
        """Test airflow pod template labels overrides."""
        env = {"name": "WORKERS_TYPE", "value": "GPU_ONLY"}
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "workers": {
                        "env": [env],
                    },
                },
            },
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert env in podTemplate["spec"]["containers"][0]["env"]

    def test_pod_template_resource_overrides(self, kube_version):
        """Test airflow pod template resources overrides."""
        resources = {
            "requests": {"cpu": "500m", "memory": "512Mi"},
            "limits": {"cpu": "1000m", "memory": "1Gi"},
        }
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "workers": {
                        "resources": resources,
                    },
                },
            },
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert "resources" in podTemplate["spec"]["containers"][0]
        assert resources == podTemplate["spec"]["containers"][0]["resources"]

    def test_pod_template_worker_securitycontext_defaults(self, kube_version):
        """Test airflow pod template security context defaults."""
        podSecurityContextDefaults = {"runAsUser": 50000, "fsGroup": 50000}
        containerSecurityContextDefaults = {"allowPrivilegeEscalation": False, "capabilities": {"drop": ["ALL"]}}
        docs = render_chart(
            kube_version=kube_version,
            values={},
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert podSecurityContextDefaults == podTemplate["spec"]["securityContext"]
        assert containerSecurityContextDefaults == podTemplate["spec"]["containers"][0]["securityContext"]

    def test_pod_template_worker_securitycontext_overrides(self, kube_version):
        """Test airflow pod template security context defaults."""
        securityContexts = {"pod": {"runAsNonRoot": False}, "container": {"allowPrivilegeEscalation": False}}
        docs = render_chart(
            kube_version=kube_version,
            values={"airflow": {"workers": {"securityContexts": securityContexts}}},
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert {"runAsNonRoot": False} == podTemplate["spec"]["securityContext"]
        assert {"allowPrivilegeEscalation": False} == podTemplate["spec"]["containers"][0]["securityContext"]

    def test_pod_template_airflow_scheduling_overrides(self, kube_version, airflow_node_pool_config):
        """Test airflow pod template scheduling overrides."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "labels": {"service": "airflow"},
                    "nodeSelector": airflow_node_pool_config["nodeSelector"],
                    "affinity": airflow_node_pool_config["affinity"],
                    "tolerations": airflow_node_pool_config["tolerations"],
                }
            },
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])

        assert podTemplate["spec"]["affinity"] == airflow_node_pool_config["affinity"]
        assert podTemplate["spec"]["nodeSelector"] == airflow_node_pool_config["nodeSelector"]
        assert podTemplate["spec"]["tolerations"] == airflow_node_pool_config["tolerations"]

    def test_pod_template_worker_scheduling_overrides(self, kube_version, airflow_node_pool_config):
        """Test that nodeSelector, affinity, and tolerations defined at the worker level take precedence over global values."""
        nodeSelector = {"role": "worker"}
        tolerations = [
            {
                "effect": "NoSchedule",
                "key": "worker",
                "operator": "Exists",
            }
        ]
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "labels": {"service": "airflow"},
                    "nodeSelector": airflow_node_pool_config["nodeSelector"],
                    "affinity": airflow_node_pool_config["affinity"],
                    "tolerations": airflow_node_pool_config["tolerations"],
                    "workers": {
                        "nodeSelector": nodeSelector,
                        "affinity": airflow_node_pool_config["affinity"],
                        "tolerations": tolerations,
                    },
                },
            },
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        common_pod_template_test(docs)
        doc = docs[0]
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])

        assert podTemplate["spec"]["affinity"] == airflow_node_pool_config["affinity"]
        assert podTemplate["spec"]["nodeSelector"] == nodeSelector
        assert podTemplate["spec"]["tolerations"] == tolerations
