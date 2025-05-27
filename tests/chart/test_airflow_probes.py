from tests.chart.helm_template_generator import render_chart

from . import get_containers_by_name


class TestAllComponentsProbes:
    def test_scheduler_probes_added(self):
        """Test that scheduler has liveness and readiness probes."""
        docs = render_chart(
            values={
                "airflow": {"airflowVersion": "2.5.0"},
                "scheduler": {"livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}},
            },
            show_only=["charts/airflow/templates/scheduler/scheduler-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])

        assert "livenessProbe" in c_by_name["scheduler"]
        assert "readinessProbe" in c_by_name["scheduler"]

        liveness_probe = c_by_name["scheduler"]["livenessProbe"]
        assert "exec" in liveness_probe
        assert "airflow jobs check --job-type SchedulerJob --local" in " ".join(liveness_probe["exec"]["command"])

    def test_triggerer_probes_added(self):
        """Test that triggerer has liveness and readiness probes."""
        docs = render_chart(
            values={
                "airflow": {"airflowVersion": "2.5.0"},
                "triggerer": {"enabled": True, "livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}},
            },
            show_only=["charts/airflow/templates/triggerer/triggerer-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])

        assert "livenessProbe" in c_by_name["triggerer"]
        assert "readinessProbe" in c_by_name["triggerer"]

        liveness_probe = c_by_name["triggerer"]["livenessProbe"]
        assert "exec" in liveness_probe
        assert "airflow jobs check --job-type TriggererJob --local" in " ".join(liveness_probe["exec"]["command"])

    def test_dag_processor_probes_added(self):
        """Test that DAG processor has liveness and readiness probes."""
        docs = render_chart(
            values={
                "airflow": {"airflowVersion": "2.5.0"},
                "dagProcessor": {"enabled": True, "livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}},
            },
            show_only=["charts/airflow/templates/dag-processor/dag-processor-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])

        assert "livenessProbe" in c_by_name["dag-processor"]
        assert "readinessProbe" in c_by_name["dag-processor"]

        liveness_probe = c_by_name["dag-processor"]["livenessProbe"]
        assert "exec" in liveness_probe
        assert "python -Wignore -c" in " ".join(liveness_probe["exec"]["command"])

    def test_workers_probes_added(self):
        """Test that workers have liveness and readiness probes."""
        docs = render_chart(
            values={
                "airflow": {"airflowVersion": "2.5.0"},
                "workers": {"livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}},
            },
            show_only=["charts/airflow/templates/workers/worker-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])

        assert "livenessProbe" in c_by_name["worker"]
        assert "readinessProbe" in c_by_name["worker"]

        liveness_probe = c_by_name["worker"]["livenessProbe"]
        assert "exec" in liveness_probe
        assert "CONNECTION_CHECK_MAX_COUNT=0 exec /entrypoint python -m celery --app" in " ".join(liveness_probe["exec"]["command"])

    def test_redis_probes_added(self):
        """Test that Redis has liveness and readiness probes."""
        docs = render_chart(
            values={
                "redis": {"enabled": True, "livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}},
            },
            show_only=["charts/airflow/templates/redis/redis-statefulset.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])

        assert "livenessProbe" in c_by_name["redis"]
        assert "readinessProbe" in c_by_name["redis"]

        liveness_probe = c_by_name["redis"]["livenessProbe"]
        assert "exec" in liveness_probe
        assert "redis-cli -a $REDIS_PASSWORD ping" in " ".join(liveness_probe["exec"]["command"])

    def test_cleanup_job_probes_added(self):
        """Test that cleanup job has liveness and readiness probes."""
        docs = render_chart(
            values={
                "cleanup": {"enabled": True, "livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}},
            },
            show_only=["charts/airflow/templates/cleanup/cleanup-cronjob.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])

        assert "livenessProbe" in c_by_name["cleanup"]
        assert "readinessProbe" in c_by_name["cleanup"]

    def test_migrate_database_job_probes_added(self):
        """Test that migrate database job has liveness and readiness probes."""
        docs = render_chart(
            values={
                "migrateDatabaseJob": {"enabled": True, "livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}},
            },
            show_only=["charts/airflow/templates/jobs/migrate-database-job.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])

        assert "livenessProbe" in c_by_name["run-airflow-migrations"]
        assert "readinessProbe" in c_by_name["run-airflow-migrations"]

    def test_log_groomer_sidecars_probes_added(self):
        """Test that log groomer sidecars have probes added."""
        docs = render_chart(
            values={
                "airflow": {"airflowVersion": "2.5.0"},
                "scheduler": {
                    "logGroomerSidecar": {"enabled": True, "livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}}
                },
                "triggerer": {
                    "enabled": True,
                    "logGroomerSidecar": {"enabled": True, "livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}},
                },
                "workers": {
                    "logGroomerSidecar": {"enabled": True, "livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}}
                },
            },
            show_only=[
                "charts/airflow/templates/scheduler/scheduler-deployment.yaml",
                "charts/airflow/templates/triggerer/triggerer-deployment.yaml",
                "charts/airflow/templates/workers/worker-deployment.yaml",
            ],
        )
        assert len(docs) == 3

        for doc in docs:
            c_by_name = get_containers_by_name(doc)

            log_groomer_containers = [name for name in c_by_name.keys() if "log-groomer" in name]

            for container_name in log_groomer_containers:
                assert "livenessProbe" in c_by_name[container_name], f"Missing liveness probe in {container_name}"
                assert "readinessProbe" in c_by_name[container_name], f"Missing readiness probe in {container_name}"

    def test_kerberos_sidecar_probes_added(self):
        """Test that kerberos sidecar has probes added."""
        docs = render_chart(
            values={
                "workers": {
                    "kerberosSidecar": {"enabled": True, "livenessProbe": {"enabled": True}, "readinessProbe": {"enabled": True}}
                },
            },
            show_only=["charts/airflow/templates/workers/worker-deployment.yaml"],
        )
        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])

        kerberos_containers = [name for name in c_by_name.keys() if "kerberos" in name.lower()]

        for container_name in kerberos_containers:
            assert "livenessProbe" in c_by_name[container_name], f"Missing liveness probe in {container_name}"
            assert "readinessProbe" in c_by_name[container_name], f"Missing readiness probe in {container_name}"

    def test_all_probes_have_default_values(self):
        """Test that all probes have the expected default values."""
        docs = render_chart(
            values={
                "airflow": {"airflowVersion": "2.5.0"},
                "scheduler": {"livenessProbe": {"enabled": True}},
                "triggerer": {"enabled": True, "livenessProbe": {"enabled": True}},
                "dagProcessor": {"enabled": True, "livenessProbe": {"enabled": True}},
                "workers": {"livenessProbe": {"enabled": True}},
                "redis": {"enabled": True, "livenessProbe": {"enabled": True}},
            },
            show_only=[
                "charts/airflow/templates/scheduler/scheduler-deployment.yaml",
                "charts/airflow/templates/triggerer/triggerer-deployment.yaml",
                "charts/airflow/templates/dag-processor/dag-processor-deployment.yaml",
                "charts/airflow/templates/workers/worker-deployment.yaml",
                "charts/airflow/templates/redis/redis-statefulset.yaml",
            ],
        )

        expected_defaults = {"initialDelaySeconds": 10, "timeoutSeconds": 20, "failureThreshold": 5, "periodSeconds": 60}

        for doc in docs:
            c_by_name = get_containers_by_name(doc)
            for container_name, container in c_by_name.items():
                if "livenessProbe" in container:
                    liveness_probe = container["livenessProbe"]
                    for key, expected_value in expected_defaults.items():
                        assert liveness_probe.get(key) == expected_value, (
                            f"Wrong {key} in {container_name}: expected {expected_value}, got {liveness_probe.get(key)}"
                        )
