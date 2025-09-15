import pytest
import yaml

from tests import supported_k8s_versions
from tests.utils.chart import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestStatsdConfigMap:
    def test_statsd_configmap_defaults(self, kube_version):
        """Test that default statsd is good"""
        docs = render_chart(
            kube_version=kube_version,
            show_only="charts/airflow/templates/configmaps/statsd-configmap.yaml",
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "ConfigMap"
        assert doc["apiVersion"] == "v1"
        yml = yaml.safe_load(doc["data"]["mappings.yml"])
        assert len(yml["mappings"]) == 19
        assert yml["mappings"][-1] == {
            "action": "drop",
            "match": ".",
            "match_type": "regex",
            "name": "dropped",
        }
