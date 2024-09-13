import textwrap

import pytest
import yaml

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestLoggingSidecar:
    def test_logging_sidecar_config_defaults(self, kube_version):
        """Test logging sidecar config with defaults"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "loggingSidecar": {"enabled": True},
                "airflow": {
                    "elasticsearch": {
                        "enabled": True,
                        "connection": {"user": "testuser", "pass": "testpass"},
                    }
                },
            },
            show_only="templates/logging-sidecar-configmap.yaml",
        )
        assert len(docs) == 1
        doc = docs[0]
        assert "ConfigMap" == doc["kind"]
        assert "v1" == doc["apiVersion"]
        vc = yaml.safe_load(doc["data"]["vector-config.yaml"])
        assert vc["sinks"]["out"]["auth"] == {
            "strategy": "basic",
            "user": "testuser",
            "password": "testpass",
        }
        assert vc["sinks"]["out"]["bulk"]["index"] == "vector.${RELEASE:--}.%Y.%m.%d"

    def test_logging_sidecar_config_disabled(self, kube_version):
        """Test logging sidecar config with flag disabled"""
        docs = render_chart(
            kube_version=kube_version,
            values={"loggingSidecar": {"enabled": False}},
            show_only="templates/logging-sidecar-configmap.yaml",
        )
        assert len(docs) == 0

    def test_logging_sidecar_custom_config(self, kube_version):
        """Test logging sidecar config with customConfig flag enabled"""
        test_custom_sidecar_config = textwrap.dedent(
            """
        loggingSidecar:
          enabled: true
          customConfig: true
          name: sidecar-logging-consumer
            """
        )
        values = yaml.safe_load(test_custom_sidecar_config)
        docs = render_chart(
            kube_version=kube_version,
            values=values,
            show_only="templates/logging-sidecar-configmap.yaml",
        )
        assert len(docs) == 0

    def test_logging_sidecar_index_format_overrides(self, kube_version):
        """Test logging sidecar config with custom timestamp format"""
        test_custom_sidecar_config = textwrap.dedent(
            """
        loggingSidecar:
          enabled: true
          name: sidecar-logging-consumer
          indexPattern: "%Y.%m"
            """
        )
        values = yaml.safe_load(test_custom_sidecar_config)
        docs = render_chart(
            kube_version=kube_version,
            values=values,
            show_only="templates/logging-sidecar-configmap.yaml",
        )
        assert len(docs) == 1
        vc = yaml.safe_load(docs[0]["data"]["vector-config.yaml"])
        assert vc["sinks"]["out"]["bulk"] == {
            "index": "vector.${RELEASE:--}.%Y.%m",
            "action": "create",
        }

    def test_logging_sidecar_index_prefix_overrides(self, kube_version):
        """Test logging sidecar config with custom index prefix"""
        test_custom_sidecar_config = textwrap.dedent(
            """
        loggingSidecar:
          enabled: true
          name: sidecar-logging-consumer
          indexNamePrefix: "fluentd"
            """
        )
        values = yaml.safe_load(test_custom_sidecar_config)
        docs = render_chart(
            kube_version=kube_version,
            values=values,
            show_only="templates/logging-sidecar-configmap.yaml",
        )
        assert len(docs) == 1
        vc = yaml.safe_load(docs[0]["data"]["vector-config.yaml"])
        assert vc["sinks"]["out"]["bulk"] == {
            "index": "fluentd.${RELEASE:--}.%Y.%m.%d",
            "action": "create",
        }
