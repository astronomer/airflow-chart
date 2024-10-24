# Beyoncé Rule tests for OSS airflow scheduler behaviors

import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions
from . import get_containers_by_name


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
            "airflow":{
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
