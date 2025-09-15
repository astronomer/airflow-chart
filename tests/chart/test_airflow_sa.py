import pytest

from tests import supported_k8s_versions
from tests.utils.chart import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAirflowServiceAccountTpl:
    def test_webserver_service_account_name_with_template(self, kube_version):
        """Test webserver service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "webserver": {
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-webserver",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/webserver/webserver-deployment.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-webserver"

    def test_scheduler_service_account_name_with_template(self, kube_version):
        """Test scheduler service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "scheduler": {
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-scheduler",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/scheduler/scheduler-deployment.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-scheduler"

    def test_workers_service_account_name_with_template(self, kube_version):
        """Test workers service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "executor": "CeleryExecutor",
                    "workers": {
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-workers",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/workers/worker-deployment.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-workers"

    def test_triggerer_service_account_name_with_template(self, kube_version):
        """Test triggerer service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "airflowVersion": "2.4.3",  # Triggerer requires Airflow 2.2+
                    "triggerer": {
                        "enabled": True,
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-triggerer",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/triggerer/triggerer-deployment.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-triggerer"

    def test_dag_processor_service_account_name_with_template(self, kube_version):
        """Test dag processor service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "airflowVersion": "2.4.3",
                    "dagProcessor": {
                        "enabled": True,
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-dag-processor",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/dag-processor/dag-processor-deployment.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-dag-processor"

    def test_flower_service_account_name_with_template(self, kube_version):
        """Test flower service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "executor": "CeleryExecutor",  # Flower is for Celery
                    "flower": {
                        "enabled": True,
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-flower",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/flower/flower-deployment.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-flower"

    def test_statsd_service_account_name_with_template(self, kube_version):
        """Test statsd service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "statsd": {
                        "enabled": True,
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-statsd",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/statsd/statsd-deployment.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-statsd"

    def test_redis_service_account_name_with_template(self, kube_version):
        """Test redis service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "executor": "CeleryExecutor",
                    "redis": {
                        "enabled": True,
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-redis",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/redis/redis-statefulset.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "StatefulSet"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-redis"

    def test_pgbouncer_service_account_name_with_template(self, kube_version):
        """Test pgbouncer service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "pgbouncer": {
                        "enabled": True,
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-pgbouncer",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/pgbouncer/pgbouncer-deployment.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-pgbouncer"

    def test_cleanup_service_account_name_with_template(self, kube_version):
        """Test cleanup service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "cleanup": {
                        "enabled": True,
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-cleanup",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/cleanup/cleanup-cronjob.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "CronJob"
        actual_sa_name = doc["spec"]["jobTemplate"]["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-cleanup"

    def test_create_user_job_service_account_name_with_template(self, kube_version):
        """Test create user job service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {  # Back under airflow namespace as per helper template
                    "createUserJob": {
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-create-user",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/jobs/create-user-job.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Job"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-create-user"

    def test_migrate_database_job_service_account_name_with_template(self, kube_version):
        """Test migrate database job service account name template processing."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "migrateDatabaseJob": {
                        "serviceAccount": {
                            "create": False,
                            "name": "custom-{{ .Release.Name }}-migrate-db",
                        },
                    },
                },
            },
            show_only=["charts/airflow/templates/jobs/migrate-database-job.yaml"],
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Job"
        actual_sa_name = doc["spec"]["template"]["spec"]["serviceAccountName"]
        assert actual_sa_name == "custom-release-name-migrate-db"
