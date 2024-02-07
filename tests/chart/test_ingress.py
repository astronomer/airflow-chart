import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestIngress:
    def test_airflow_ingress_defaults(self, kube_version):
        """Test airflow ingress with defaults - KubernetesExecutor."""
        docs = render_chart(
            kube_version=kube_version,
            values={"ingress": {"enabled": True}},
            show_only="templates/ingress.yaml",
        )
        assert len(docs) == 1
        doc = docs[0]
        assert "Ingress" == doc["kind"]
        assert "networking.k8s.io/v1" == doc["apiVersion"]

    def test_airflow_ingress_with_celery_executor(self, kube_version):
        """Test airflow ingress with CeleryExecutor."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {"executor": "CeleryExecutor"},
                "ingress": {"enabled": True},
            },
            show_only="templates/ingress.yaml",
        )
        assert len(docs) == 2
        doc = docs[0]
        assert "Ingress" == doc["kind"]
        assert "networking.k8s.io/v1" == doc["apiVersion"]
        doc = docs[1]
        assert "Ingress" == doc["kind"]
        assert "networking.k8s.io/v1" == doc["apiVersion"]
