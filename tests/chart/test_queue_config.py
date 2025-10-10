import pytest

from tests import supported_k8s_versions
from tests.utils.chart import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
@pytest.mark.parametrize(
    "airflow_version,expected_queue",
    [
        ("2.10.2", "celery"),
        ("3.0.0", "default"),
        ("3.1.0", "default"),
    ],
)
class TestQueueConfig:
    def test_default_queue_configuration(self, kube_version, airflow_version, expected_queue):
        """Test that default_queue is set correctly based on Airflow version"""
        docs = render_chart(
            kube_version=kube_version,
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
            values={
                "airflow": {
                    "airflowVersion": airflow_version,
                },
            },
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "ConfigMap"

        # Check that airflow.cfg contains the correct default_queue settings
        airflow_cfg = doc["data"]["airflow.cfg"]
        assert f"default_queue = {expected_queue}" in airflow_cfg
        assert "[operators]" in airflow_cfg
        assert "[celery]" in airflow_cfg
