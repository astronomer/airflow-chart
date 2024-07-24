import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestIngress:
    def test_airflow_ingress_defaults(self, kube_version):
        """Test airflow ingress with defaults - KubernetesExecutor."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/ingress.yaml",
            values={"ingress": {"enabled": True, "baseDomain": "example.com"}},
        )
        assert len(docs) == 1
        doc = docs[0]
        assert "Ingress" == doc["kind"]
        assert "networking.k8s.io/v1" == doc["apiVersion"]
        assert "/release-name/airflow" == docs[0]["spec"]["rules"][0]["http"]["paths"][0]["path"]

    def test_airflow_ingress_with_celery_executor(self, kube_version):
        """Test airflow ingress with CeleryExecutor."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/ingress.yaml",
            values={
                "airflow": {"executor": "CeleryExecutor"},
                "ingress": {"enabled": True, "baseDomain": "example.com"},
            },
        )
        assert len(docs) == 2

        doc = docs[0]
        assert "Ingress" == doc["kind"]
        assert "networking.k8s.io/v1" == doc["apiVersion"]
        assert "/release-name/airflow" == docs[0]["spec"]["rules"][0]["http"]["paths"][0]["path"]

        doc = docs[1]
        assert "Ingress" == doc["kind"]
        assert "networking.k8s.io/v1" == doc["apiVersion"]
        assert "/release-name/airflow" == docs[0]["spec"]["rules"][0]["http"]["paths"][0]["path"]

    def test_airflow_ingress_with_dag_server(self, kube_version):
        """Test airflow ingress with DagServer."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/ingress.yaml",
            values={
                "ingress": {"baseDomain": "example.com"},
                "dagDeploy": {"enabled": True},
            },
        )

        assert len(docs) == 1
        assert docs[0]["metadata"]["name"] == "release-name-dag-server-ingress"
        rule_0 = docs[0]["spec"]["rules"][0]
        assert rule_0["http"]["paths"][0]["path"] == "/release-name/dags/(upload|download)(/.*)?"
        assert rule_0["host"] == "deployments.example.com"

    def test_airflow_ingress_with_dag_server_ingress_annotation(self, kube_version):
        """Test airflow ingress with DagServer."""

        ingressAnnotation = {"kubernetes.io/ingress.class": "default"}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/ingress.yaml",
            values={
                "ingress": {
                    "enabled": True,
                    "baseDomain": "example.com",
                    "dagServerAnnotations": ingressAnnotation,
                },
                "dagDeploy": {"enabled": True},
            },
        )

        assert len(docs) == 2

        assert docs[1]["metadata"]["name"] == "release-name-dag-server-ingress"
        rule_0 = docs[1]["spec"]["rules"][0]
        assert (
            rule_0["http"]["paths"][0]["path"]
            == "/release-name/dags/(upload|download)(/.*)?"
        )
        assert rule_0["host"] == "deployments.example.com"

        assert ingressAnnotation == docs[1]["metadata"]["annotations"]
