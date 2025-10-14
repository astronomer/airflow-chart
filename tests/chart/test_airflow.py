# Beyoncé Rule tests for OSS airflow scheduler behaviors

import pytest

from tests import supported_k8s_versions
from tests.utils import get_containers_by_name
from tests.utils.chart import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAirflow:
    def test_migrate_database_job_defaults(self, kube_version):
        """Test custom behaviors of the scheduler that we rely on."""
        docs = render_chart(
            kube_version=kube_version, show_only=["charts/airflow/templates/jobs/migrate-database-job.yaml"], values={}
        )

        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert {"name": "PYTHONUNBUFFERED", "value": "1"} in c_by_name["run-airflow-migrations"]["env"]

    def test_migrate_database_job_overrides(self, kube_version):
        """Test custom behaviors of the scheduler that we rely on."""
        env = {"name": "ENABLE_AUTH_TYPE", "value": "SHA256"}
        values = {
            "airflow": {
                "migrateDatabaseJob": {
                    "env": [env],
                }
            }
        }
        docs = render_chart(
            kube_version=kube_version, show_only=["charts/airflow/templates/jobs/migrate-database-job.yaml"], values=values
        )

        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert {"name": "PYTHONUNBUFFERED", "value": "1"} in c_by_name["run-airflow-migrations"]["env"]
        assert {"name": "ENABLE_AUTH_TYPE", "value": "SHA256"} in c_by_name["run-airflow-migrations"]["env"]

    def test_airflow_apiserver_defaults(self, kube_version):
        """Test Airflow3 apiServer defaults."""
        values = {"airflow": {"airflowVersion": "3.0.0"}}
        docs = render_chart(
            kube_version=kube_version,
            show_only=[
                "charts/airflow/templates/api-server/api-server-deployment.yaml",
                "templates/api-server/api-server-execution-networkpolicy.yaml",
            ],
            values=values,
        )

        assert len(docs) == 1
        assert docs[0]["spec"]["template"]["spec"]["serviceAccountName"] == "release-name-airflow-api-server"

    def test_airflow_apiserver_with_networkpolicy(self, kube_version):
        """Test Airflow3 apiServer defaults."""
        values = {"airflow": {"airflowVersion": "3.0.0", "networkPolicies": {"enabled": True}}}
        docs = render_chart(
            kube_version=kube_version,
            show_only=[
                "templates/api-server/api-server-execution-networkpolicy.yaml",
                "charts/airflow/templates/api-server/api-server-deployment.yaml",
            ],
            values=values,
        )

        assert len(docs) == 2
        spec = docs[0]["spec"]
        print(spec["ingress"][0]["from"][0])
        assert {
            "namespaceSelector": {},
            "podSelector": {"matchLabels": {"component": "worker", "release": "release-name", "tier": "airflow"}},
        } == spec["ingress"][0]["from"][0]
