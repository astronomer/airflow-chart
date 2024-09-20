import pytest
import yaml
from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestPodTemplate:
    def test_pod_template_defaults(self, kube_version):
        """Test airflow pod template defaults."""
        docs = render_chart(
            kube_version=kube_version,
            values={},
            show_only="charts/airflow/templates/configmaps/configmap.yaml",
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "ConfigMap"
        podTemplate = yaml.safe_load(doc["data"]["pod_template_file.yaml"])
        assert {"tier": "airflow", "component": "worker", "release": "release-name"} == podTemplate["metadata"]["labels"]
