# https://github.com/astronomer/issues/issues/6214


import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAffinity:
    affinity_files = [
        "charts/airflow/templates/flower/flower-deployment.yaml",
        "charts/airflow/templates/pgbouncer/pgbouncer-deployment.yaml",
        "charts/airflow/templates/redis/redis-statefulset.yaml",
        "charts/airflow/templates/scheduler/scheduler-deployment.yaml",
        "charts/airflow/templates/statsd/statsd-deployment.yaml",
        "charts/airflow/templates/webserver/webserver-deployment.yaml",
        "charts/airflow/templates/workers/worker-deployment.yaml",
    ]

    def test_scheduler_global_affinity(self, kube_version):
        """Test that airflow chart affinity is set correctly when using our default values."""

        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "flower": {"enabled": True},
                    "pgbouncer": {"enabled": True},
                    "executor": "CeleryExecutor",
                }
            },
            show_only=self.affinity_files,
        )
        assert len(docs) == 7
        assert [
            doc.get("spec").get("template").get("spec").get("affinity") for doc in docs
        ] == [
            {},
            {},
            {},
            {
                "podAntiAffinity": {
                    "preferredDuringSchedulingIgnoredDuringExecution": [
                        {
                            "podAffinityTerm": {
                                "labelSelector": {
                                    "matchExpressions": [
                                        {
                                            "key": "component",
                                            "operator": "In",
                                            "values": ["scheduler"],
                                        }
                                    ]
                                },
                                "topologyKey": "kubernetes.io/hostname",
                            },
                            "weight": 100,
                        }
                    ]
                }
            },
            {},
            {
                "podAntiAffinity": {
                    "preferredDuringSchedulingIgnoredDuringExecution": [
                        {
                            "podAffinityTerm": {
                                "labelSelector": {
                                    "matchLabels": {"component": "webserver"}
                                },
                                "topologyKey": "kubernetes.io/hostname",
                            },
                            "weight": 100,
                        }
                    ]
                }
            },
            {
                "podAntiAffinity": {
                    "preferredDuringSchedulingIgnoredDuringExecution": [
                        {
                            "podAffinityTerm": {
                                "labelSelector": {
                                    "matchLabels": {"component": "worker"}
                                },
                                "topologyKey": "kubernetes.io/hostname",
                            },
                            "weight": 100,
                        }
                    ]
                }
            },
        ]
