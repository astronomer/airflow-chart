from tests.chart.helm_template_generator import render_chart


class TestTriggerer:
    def test_triggerer_log_grommer_defaults(self):
        """Test Triggerer  Log Groomer defaults."""
        docs = render_chart(
            values={
                "airflow": {"airflowVersion": "2.4.3"},
            },
            show_only=["charts/airflow/templates/triggerer/triggerer-deployment.yaml"],
        )
        assert len(docs) == 1
        assert (
            "/usr/local/bin/clean-airflow-logs"
            in docs[0]["spec"]["template"]["spec"]["containers"][1]["args"]
        )
