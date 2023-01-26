import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestWorkerHpa:
    def test_worker_hpa_defaults(self, kube_version):
        """Test worker hpa with defaults - disabled."""
        docs = render_chart(
            kube_version=kube_version,
            values={},
            show_only="templates/workers/worker-horizontalpodautoscaler.yaml",
        )
        assert len(docs) == 0

    def test_worker_hpa_enabled(self, kube_version):
        """Test worker hpa  enabled - CeleryExecutor."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {"executor": "CeleryExecutor"},
                "workers": {"autoscaling": {"enabled": True}},
            },
            show_only="templates/workers/worker-horizontalpodautoscaler.yaml",
        )
        assert len(docs) == 1
        doc = docs[0]
        assert "HorizontalPodAutoscaler" == doc["kind"]
        _, minor, _ = (int(x) for x in kube_version.split("."))
        if minor >= 25:
            assert "autoscaling/v2" == doc["apiVersion"]
        else:
            assert "autoscaling/v2beta1" == doc["apiVersion"]

    def test_worker_hpa_metrics(self, kube_version):
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {"executor": "CeleryExecutor"},
                "workers": {"autoscaling": {"enabled": True}},
            },
            show_only="templates/workers/worker-horizontalpodautoscaler.yaml",
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["spec"]["metrics"][0]["resource"]["name"] == "cpu"
        assert doc["spec"]["metrics"][1]["resource"]["name"] == "memory"
        _, minor, _ = (int(x) for x in kube_version.split("."))
        if minor >= 25:
            assert (
                doc["spec"]["metrics"][0]["resource"]["target"]["averageUtilization"]
                == 80
            )
            assert (
                doc["spec"]["metrics"][1]["resource"]["target"]["averageUtilization"]
                == 80
            )
        else:
            assert (
                doc["spec"]["metrics"][0]["resource"]["targetAverageUtilization"] == 80
            )
            assert (
                doc["spec"]["metrics"][1]["resource"]["targetAverageUtilization"] == 80
            )
