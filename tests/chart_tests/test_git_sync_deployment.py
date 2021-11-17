import jmespath
import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestIngress:
    def test_git_sync_deployment_default(self, kube_version):
        """Test that each template used with just baseDomain set renders."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync/git-sync-deployment.yaml",
        )
        assert len(docs) == 0

    def test_git_sync_deployment_git_sync_enabled(self, kube_version):
        """Test that each template used with just baseDomain set renders."""
        values = {"airflow": {"dags": {"gitSync": {"enabled": True}}}}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync/git-sync-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "RELEASE-NAME-git-sync"
        assert any(
            image_name.startswith("quay.io/astronomer/ap-git-sync:")
            for image_name in jmespath.search(
                "spec.template.spec.containers[*].image", doc
            )
        )
        assert len(doc["spec"]["template"]["spec"]["containers"]) == 1
