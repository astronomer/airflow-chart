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

    def test_scheduler_liveness_and_readiness_probes_are_configurable_with_gitsync_enabled(self, kube_version):
        livenessProbe = {
            "failureThreshold": 10,
            "exec": {"command": ["/bin/true"]},
            "initialDelaySeconds": 0,
            "periodSeconds": 1,
            "timeoutSeconds": 5,
        }
        readinessProbe = {
            "failureThreshold": 10,
            "exec": {"command": ["/bin/true"]},
            "initialDelaySeconds": 0,
            "periodSeconds": 1,
            "timeoutSeconds": 5,
        }
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "airflowVersion": "2.4.3",
                    "dags": {
                        "gitSync": {
                            "enabled": True,
                            "livenessProbe": livenessProbe,
                            "readinessProbe": readinessProbe,
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/scheduler/scheduler-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0], include_init_containers=True)
        assert "livenessProbe" in c_by_name["git-sync"]
        assert "readinessProbe" in c_by_name["git-sync"]
        assert "readinessProbe" not in c_by_name["git-sync-init"]
        assert "readinessProbe" not in c_by_name["git-sync-init"]
        assert livenessProbe == c_by_name["git-sync"]["livenessProbe"]
        assert readinessProbe == c_by_name["git-sync"]["readinessProbe"]
