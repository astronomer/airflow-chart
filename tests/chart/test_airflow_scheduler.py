# Beyoncé Rule tests for OSS airflow scheduler behaviors

import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAirflowScheduler:
    def test_scheduler_defaults(self, kube_version):
        """Test default behaviors of the scheduler that we rely on."""
        docs = render_chart(kube_version=kube_version, show_only=["charts/airflow/templates/scheduler/scheduler-deployment.yaml"])

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["spec"]["strategy"] == {"type": "Recreate"}

    def test_scheduler_customizations(self, kube_version):
        """Test custom behaviors of the scheduler that we rely on."""
        values = {"airflow": {"scheduler": {"strategy": {"type": "RollingUpdate"}}}}
        docs = render_chart(
            kube_version=kube_version, show_only=["charts/airflow/templates/scheduler/scheduler-deployment.yaml"], values=values
        )

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["spec"]["strategy"] == {"type": "RollingUpdate"}
