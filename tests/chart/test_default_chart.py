import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


@pytest.mark.parametrize("namespace", ["abc", "123", "123abc", "123-abc"])
def test_namespace_names(namespace):
    """Test various namespace names to make sure they render correctly in templates"""
    render_chart(namespace=namespace)


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestDefaultChart:
    def test_default_chart_with_basedomain(self, kube_version):
        """Test that each template used with just baseDomain set renders."""
        docs = render_chart(kube_version=kube_version)
        assert len(docs) == 31

    def test_default_labels(self, kube_version):
        """Test that extra-objects works as default."""
        docs = render_chart(kube_version=kube_version)
        exclusions = ["release-name-postgresql", "release-name-postgresql-hl"]

        for doc in docs:
            if doc["metadata"]["name"] in exclusions:
                continue
            assert doc["metadata"]["labels"]["chart"].startswith("airflow")
            assert doc["metadata"]["labels"]["release"] == "release-name"
            assert doc["metadata"]["labels"]["tier"] == "airflow"
            assert doc["metadata"]["labels"]["heritage"] == "Helm"

        assert all(bool(x) for x in doc["metadata"]["labels"].values())
