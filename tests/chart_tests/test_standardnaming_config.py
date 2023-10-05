from tests.chart_tests.helm_template_generator import render_chart


class TestAirflowDefaults:
    def test_use_standard_naming_defaults(self):
        """Test useStandardNaming feature defaults."""
        docs = render_chart(
            values={"airflow": {"executor": "CeleryExecutor"}},
            show_only=[
                "charts/airflow/templates/configmaps/configmap.yaml",
                "charts/airflow/templates/secrets/metadata-connection-secret.yaml",
                "charts/airflow/templates/secrets/result-backend-connection-secret.yaml",
            ],
        )
        # print(docs)
        assert len(docs) == 3
        assert docs[0]["kind"] == "ConfigMap"
        assert docs[0]["apiVersion"] == "v1"
        assert docs[0]["metadata"]["name"] == "release-name-airflow-config"
        assert docs[1]["kind"] == "Secret"
        assert docs[1]["apiVersion"] == "v1"
        assert docs[1]["metadata"]["name"] == "release-name-airflow-metadata"
        assert docs[2]["kind"] == "Secret"
        assert docs[2]["apiVersion"] == "v1"
        assert docs[2]["metadata"]["name"] == "release-name-airflow-result-backend"

    def test_use_standard_naming_overrides(self):
        """Test useStandardNaming feature overrides."""
        docs = render_chart(
            values={
                "airflow": {"executor": "CeleryExecutor", "useStandardNaming": False}
            },
            show_only=[
                "charts/airflow/templates/configmaps/configmap.yaml",
                "charts/airflow/templates/secrets/metadata-connection-secret.yaml",
                "charts/airflow/templates/secrets/result-backend-connection-secret.yaml",
            ],
        )
        assert len(docs) == 3
        assert docs[0]["kind"] == "ConfigMap"
        assert docs[0]["apiVersion"] == "v1"
        assert docs[0]["metadata"]["name"] == "release-name-config"
        assert docs[1]["kind"] == "Secret"
        assert docs[1]["apiVersion"] == "v1"
        assert docs[1]["metadata"]["name"] == "release-name-metadata"
        assert docs[2]["kind"] == "Secret"
        assert docs[2]["apiVersion"] == "v1"
        assert docs[2]["metadata"]["name"] == "release-name-result-backend"
