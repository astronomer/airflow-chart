# Beyoncé Rule tests for OSS airflow scheduler behaviors

import pytest

from tests import supported_k8s_versions
from tests.utils import get_all_features, get_containers_by_name
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

    def test_migrate_database_job_with_preAirflowExtraInitContainers(self, kube_version):
        """Test migrate database job behaviors with preAirflowExtraInitContainers."""
        docs = render_chart(
            kube_version=kube_version,
            show_only=["charts/airflow/templates/jobs/migrate-database-job.yaml"],
            values=get_all_features(),
        )

        assert len(docs) == 1
        assert "initContainers" in docs[0]["spec"]["template"]["spec"]
        c_by_name = get_containers_by_name(docs[0], include_init_containers=True)
        assert "usr-local-airflow-copier" in c_by_name
        assert c_by_name["usr-local-airflow-copier"]["securityContext"]["readOnlyRootFilesystem"] is True

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
        ingress_spec = docs[0]["spec"]["ingress"]
        assert len(ingress_spec) == 1
        assert ingress_spec[0]["from"][0] == {
            "namespaceSelector": {},
            "podSelector": {
                "matchLabels": {
                    "component": "worker",
                    "release": "release-name",
                    "tier": "airflow",
                }
            },
        }

    def test_webserver_startup_initialDelaySeconds_defaults(self, kube_version):
        """Test initialDelaySeconds defaults."""
        docs = render_chart(
            kube_version=kube_version, show_only=["charts/airflow/templates/webserver/webserver-deployment.yaml"], values={}
        )

        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert c_by_name["webserver"]["startupProbe"]["initialDelaySeconds"] == 30

    def test_apiServer_startup_initialDelaySeconds_defaults(self, kube_version):
        """Test initialDelaySeconds defaults."""
        values = {"airflow": {"airflowVersion": "3.0.0"}}
        docs = render_chart(
            kube_version=kube_version, show_only=["charts/airflow/templates/api-server/api-server-deployment.yaml"], values=values
        )

        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert c_by_name["api-server"]["startupProbe"]["initialDelaySeconds"] == 30
