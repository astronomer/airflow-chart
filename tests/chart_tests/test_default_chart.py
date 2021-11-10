from tests.chart_tests.helm_template_generator import render_chart


def test_default_chart_with_basedomain(template):
    """Test that each template used with just baseDomain set renders."""
    docs = render_chart(
        show_only=[template["name"]],
    )
    assert len(docs) == template["length"]
