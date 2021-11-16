import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestIngress:
    def test_git_sync_service_default(self, kube_version):
        """Test that each template used with just baseDomain set renders."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync/git-sync-service.yaml",
        )
        assert len(docs) == 0

    def test_git_sync_service_git_sync_enabled(self, kube_version):
        """Test that each template used with just baseDomain set renders."""
        values = {"airflow": {"dags": {"gitSync": {"enabled": True}}}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync/git-sync-service.yaml",
            values=values,
        )
        assert len(docs) == 1
