import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestQueueConfig:
    def test_default_queue_airflow_2_x(self, kube_version):
        """Test that default_queue is set to 'celery' for Airflow 2.x versions"""
        docs = render_chart(
            kube_version=kube_version,
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
            values={
                "airflow": {
                    "airflowVersion": "2.10.2",
                },
            },
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "ConfigMap"

        # Check that airflow.cfg contains the correct default_queue settings
        airflow_cfg = doc["data"]["airflow.cfg"]
        assert "default_queue = celery" in airflow_cfg
        assert "[operators]" in airflow_cfg
        assert "[celery]" in airflow_cfg

    def test_default_queue_airflow_3_x(self, kube_version):
        """Test that default_queue is set to 'default' for Airflow 3.x versions"""
        docs = render_chart(
            kube_version=kube_version,
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
            values={
                "airflow": {
                    "airflowVersion": "3.0.0",
                },
            },
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "ConfigMap"

        # Check that airflow.cfg contains the correct default_queue settings
        airflow_cfg = doc["data"]["airflow.cfg"]
        assert "default_queue = default" in airflow_cfg
        assert "[operators]" in airflow_cfg
        assert "[celery]" in airflow_cfg

    def test_default_queue_airflow_3_1(self, kube_version):
        """Test that default_queue is set to 'default' for Airflow 3.1.x versions"""
        docs = render_chart(
            kube_version=kube_version,
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
            values={
                "airflow": {
                    "airflowVersion": "3.1.0",
                },
            },
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "ConfigMap"

        # Check that airflow.cfg contains the correct default_queue settings
        airflow_cfg = doc["data"]["airflow.cfg"]
        assert "default_queue = default" in airflow_cfg
        assert "[operators]" in airflow_cfg
        assert "[celery]" in airflow_cfg
