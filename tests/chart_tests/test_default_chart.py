from tests.chart_tests.helm_template_generator import render_chart


def test_default_chart_with_basedomain():
    """Test that each template used with just baseDomain set renders."""
    docs = render_chart()
    assert len(docs) == 26
