import pytest
import yaml
from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


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
