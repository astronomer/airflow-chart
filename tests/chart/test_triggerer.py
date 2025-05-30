from tests.chart.helm_template_generator import render_chart

from . import get_containers_by_name


class TestTriggerer:
    def test_triggerer_log_grommer_defaults(self):
        """Test Triggerer  Log Groomer defaults."""
        default_env_vars = [
            {"name": "AIRFLOW__LOG_RETENTION_DAYS", "value": "333"},
            {"name": "AIRFLOW_HOME", "value": "/some/dummy/airflow_home"},
        ]
        docs = render_chart(
            values={
                "airflow": {"airflowVersion": "10.20.30"},
            },
            show_only=["charts/airflow/templates/triggerer/triggerer-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert "/usr/local/bin/clean-airflow-logs" in c_by_name["triggerer-log-groomer"]["args"]
        assert default_env_vars == c_by_name["triggerer-log-groomer"]["env"]

    def test_triggerer_log_grommer_overrides(self):
        """Test Triggerer  Log Groomer with custom env vars."""
        env = {"name": "ASTRONOMER__AIRFLOW___LOG_RETENTION_DAYS", "value": "777"}
        docs = render_chart(
            values={
                "airflow": {
                    "airflowVersion": "40.50.60",
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
        """Test Triggerer liveness and readiness probes are configurable with git sync enabled."""
        git_sync_livenessProbe = {
            "failureThreshold": 999,
            "exec": {"command": ["/dummy/livenessProbe"]},
            "initialDelaySeconds": 999,
            "periodSeconds": 999,
            "timeoutSeconds": 999,
        }
        git_sync_readinessProbe = {
            "failureThreshold": 888,
            "exec": {"command": ["/dummy/redinessProbe"]},
            "initialDelaySeconds": 888,
            "periodSeconds": 888,
            "timeoutSeconds": 888,
        }
        triggerer_liveness_probe_data = {
            "initialDelaySeconds": 777,
            "timeoutSeconds": 777,
            "failureThreshold": 777,
            "periodSeconds": 777,
            "command": ["/dummy/airflow/livenessProbe"],
        }
        triggerer_readiness_probe_data = {
            "initialDelaySeconds": 666,
            "timeoutSeconds": 666,
            "failureThreshold": 666,
            "periodSeconds": 666,
            "command": ["/dummy/airflow/readinessProbe"],
        }
        values = {
            "airflow": {
                "airflowVersion": "70.80.90",
                "dags": {
                    "gitSync": {
                        "enabled": True,
                        "livenessProbe": git_sync_livenessProbe,
                        "readinessProbe": git_sync_readinessProbe,
                    },
                },
                "triggerer": {
                    "logGroomerSidecar": {
                        "enabled": True,
                        "livenessProbe": triggerer_liveness_probe_data,
                        "readinessProbe": triggerer_readiness_probe_data,
                    },
                },
            },
        }

        docs = render_chart(values=values, show_only=["charts/airflow/templates/triggerer/triggerer-deployment.yaml"])
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0], include_init_containers=True)
        assert "livenessProbe" not in c_by_name["git-sync-init"]
        assert "readinessProbe" not in c_by_name["git-sync-init"]

        assert c_by_name["git-sync"]["livenessProbe"] == git_sync_livenessProbe
        assert c_by_name["git-sync"]["readinessProbe"] == git_sync_readinessProbe
        assert c_by_name["triggerer-log-groomer"]["livenessProbe"] == triggerer_liveness_probe_data
        assert c_by_name["triggerer-log-groomer"]["readinessProbe"] == triggerer_readiness_probe_data
