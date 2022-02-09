from tests.chart_tests.helm_template_generator import render_chart
import pytest


def test_default_chart_with_basedomain():
    """Test that each template used with just baseDomain set renders."""
    docs = render_chart()
    assert len(docs) == 26


@pytest.mark.parametrize("namespace", ["abc", "123", "123abc", "123-abc"])
def test_namespace_names(self, namespace):
    """Test various namespace names to make sure they render correctly in templates"""
    render_chart(namespace=namespace)
