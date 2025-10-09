from tests.utils import get_containers_by_name
from tests.utils.chart import render_chart


class TestDagProcessor:
    def test_dag_processor_defaults(self):
        """Test Dag Processor defaults."""
        docs = render_chart(
            values={},
            show_only=[
                "charts/airflow/templates/dag-processor/dag-processor-deployment.yaml",
                "charts/airflow/templates/dag-processor/dag-processor-serviceaccount.yaml",
            ],
        )
        assert len(docs) == 0

    def test_dag_processor_enabled_with_log_grommer_defaults(self):
        """Test Dag Processor enabled defaults with log groomer."""
        default_env_vars = [
            {"name": "AIRFLOW__LOG_RETENTION_DAYS", "value": "15"},
            {"name": "AIRFLOW__LOG_CLEANUP_FREQUENCY_MINUTES", "value": "15"},
            {"name": "AIRFLOW_HOME", "value": "/usr/local/airflow"},
        ]
        docs = render_chart(
            values={
                "airflow": {"airflowVersion": "2.4.3", "dagProcessor": {"enabled": True}},
            },
            show_only=["charts/airflow/templates/dag-processor/dag-processor-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert "/usr/local/bin/clean-airflow-logs" in c_by_name["dag-processor-log-groomer"]["args"]
        assert default_env_vars == c_by_name["dag-processor-log-groomer"]["env"]

    def test_dag_processor_enbaled_with_log_grommer_overrides(self):
        """Test Dag Processor enabled defaults with log groomer custom env vars."""
        env = {"name": "ASTRONOMER__AIRFLOW___LOG_RETENTION_DAYS", "value": "5"}
        docs = render_chart(
            values={
                "airflow": {
                    "airflowVersion": "2.4.3",
                    "dagProcessor": {"enabled": True, "logGroomerSidecar": {"env": [env]}},
                },
            },
            show_only=["charts/airflow/templates/dag-processor/dag-processor-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert "/usr/local/bin/clean-airflow-logs" in c_by_name["dag-processor-log-groomer"]["args"]
        assert env in c_by_name["dag-processor-log-groomer"]["env"]

    def test_dag_processor_deployment_enabled_with_defaults(self):
        """Test dag processor defaults."""

        docs = render_chart(
            values={
                "airflow": {
                    "airflowVersion": "2.4.3",
                    "dagProcessor": {"enabled": True},
                },
            },
            show_only=["charts/airflow/templates/dag-processor/dag-processor-deployment.yaml"],
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-dag-processor"
        assert doc["spec"]["template"]["spec"]["serviceAccountName"] == "release-name-airflow-dag-processor"
        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 2
