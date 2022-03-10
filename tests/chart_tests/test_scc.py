import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAirflowsccprivileges:
    def test_scc_privileges_defaults(self, kube_version):
        """Test sairflow cc privileges with defaults - disabled."""
        docs = render_chart(
            kube_version="v4.1.0",
            values={},
            show_only="templates/airflow-scc-anyuid.yaml",
        )
        assert len(docs) == 0
