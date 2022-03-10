import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestWorkerHPA:
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
