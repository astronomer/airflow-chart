# Beyoncé Rule tests for OSS airflow scheduler behaviors

import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart

from . import get_containers_by_name


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAirflowScheduler:
    def test_scheduler_defaults(self, kube_version):
        """Test default behaviors of the scheduler that we rely on."""
        docs = render_chart(kube_version=kube_version, show_only=["charts/airflow/templates/scheduler/scheduler-deployment.yaml"])

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["spec"]["strategy"] == {"type": "Recreate"}

    def test_scheduler_customizations(self, kube_version):
        """Test custom behaviors of the scheduler that we rely on."""
        values = {"airflow": {"scheduler": {"strategy": {"type": "RollingUpdate"}}}}
        docs = render_chart(
            kube_version=kube_version, show_only=["charts/airflow/templates/scheduler/scheduler-deployment.yaml"], values=values
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["spec"]["strategy"] == {"type": "RollingUpdate"}

    def test_scheduler_log_grommer_defaults(self, kube_version):
        """Test Scheduler  Log Groomer defaults."""
        default_env_vars = [
            {"name": "AIRFLOW__LOG_RETENTION_DAYS", "value": "15"},
            {"name": "AIRFLOW_HOME", "value": "/usr/local/airflow"},
        ]
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {"airflowVersion": "2.4.3"},
            },
            show_only=["charts/airflow/templates/scheduler/scheduler-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert "/usr/local/bin/clean-airflow-logs" in c_by_name["scheduler-log-groomer"]["args"]
        print(c_by_name["scheduler-log-groomer"]["env"])
        assert default_env_vars == c_by_name["scheduler-log-groomer"]["env"]

    def test_scheduler_log_grommer_overrides(self, kube_version):
        """Test Scheduler  Log Groomer defaults."""
        env = {"name": "ASTRONOMER__AIRFLOW___LOG_RETENTION_DAYS", "value": "5"}
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "airflowVersion": "2.4.3",
                    "scheduler": {"logGroomerSidecar": {"env": [env]}},
                },
            },
            show_only=["charts/airflow/templates/scheduler/scheduler-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert "/usr/local/bin/clean-airflow-logs" in c_by_name["scheduler-log-groomer"]["args"]
        assert env in c_by_name["scheduler-log-groomer"]["env"]
