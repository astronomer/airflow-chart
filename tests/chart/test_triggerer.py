from tests.chart.helm_template_generator import render_chart

from . import get_containers_by_name


class TestTriggerer:
    def test_triggerer_log_grommer_defaults(self):
        """Test Triggerer  Log Groomer defaults."""
        default_env_vars = [
            {"name": "AIRFLOW__LOG_RETENTION_DAYS", "value": "15"},
            {"name": "AIRFLOW_HOME", "value": "/usr/local/airflow"},
        ]
        docs = render_chart(
            values={
                "airflow": {"airflowVersion": "2.4.3"},
            },
            show_only=["charts/airflow/templates/triggerer/triggerer-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert "/usr/local/bin/clean-airflow-logs" in c_by_name["triggerer-log-groomer"]["args"]
        assert default_env_vars == c_by_name["triggerer-log-groomer"]["env"]

    def test_triggerer_log_grommer_overrides(self):
        """Test Triggerer  Log Groomer with custom env vars."""
        env = {"name": "ASTRONOMER__AIRFLOW___LOG_RETENTION_DAYS", "value": "5"}
        docs = render_chart(
            values={
                "airflow": {
                    "airflowVersion": "2.4.3",
                    "triggerer": {"logGroomerSidecar": {"env": [env]}},
                },
            },
            show_only=["charts/airflow/templates/triggerer/triggerer-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert "/usr/local/bin/clean-airflow-logs" in c_by_name["triggerer-log-groomer"]["args"]
        assert env in c_by_name["triggerer-log-groomer"]["env"]

    def test_triggerer_liveness_and_readiness_probes_are_configurable_with_gitsync_enabled(self):
        livenessProbe = {
            "failureThreshold": 10,
            "exec": {"command": ["/bin/true"]},
            "initialDelaySeconds": 0,
            "periodSeconds": 1,
            "successThreshold": 1,
            "timeoutSeconds": 5,
        }
        readinessProbe = {
            "failureThreshold": 10,
            "exec": {"command": ["/bin/true"]},
            "initialDelaySeconds": 0,
            "periodSeconds": 1,
            "successThreshold": 1,
            "timeoutSeconds": 5,
        }
        docs = render_chart(
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
            show_only=["charts/airflow/templates/triggerer/triggerer-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0], include_init_containers=True)
        assert "livenessProbe" in c_by_name["git-sync"]
        assert "readinessProbe" in c_by_name["git-sync"]
        assert "readinessProbe" not in c_by_name["git-sync-init"]
        assert "readinessProbe" not in c_by_name["git-sync-init"]
        assert livenessProbe == c_by_name["git-sync"]["livenessProbe"]
        assert readinessProbe == c_by_name["git-sync"]["readinessProbe"]
