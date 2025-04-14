import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAirflowSccPrivileges:
    def test_scc_privileges_defaults(self, kube_version):
        """Test airflow scc privileges with defaults - disabled."""
        docs = render_chart(
            kube_version=kube_version,
            values={},
            show_only="templates/airflow-scc-anyuid.yaml",
        )
        assert len(docs) == 0

    def test_scc_privileges_enabled(self, kube_version):
        """Test airflow scc privileges with defaults - disabled."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "sccEnabled": True
            },
            show_only="templates/airflow-scc-anyuid.yaml",
        )
        assert len(docs) == 1
