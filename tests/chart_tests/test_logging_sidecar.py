import pytest
import yaml

from tests.chart_tests.helm_template_generator import render_chart

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
        assert (vc := yaml.safe_load(doc["data"]["vector-config.yaml"]))
        assert vc["sinks"]["out"]["auth"] == {
            "strategy": "basic",
            "user": "testuser",
            "password": "testpass",
        }

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
        airflowSidecarConfig = """
  airflowSidecarConfig: |2
      log_schema:
        timestamp_key : "@timestamp"
      data_dir: "${SIDECAR_LOGS}"
      sources:
        generate_syslog:
          type: file
          include:
            - "${SIDECAR_LOGS}/*.log"
          read_from: beginning
      transforms:
        transform_syslog:
          type: add_fields
          inputs:
            - generate_syslog
          fields:
            component: "${COMPONENT:--}"
            workspace: "${WORKSPACE:--}"
            release: "${RELEASE:--}"
      sinks:
        out:
          type: datadog
          inputs:
            - transform_syslog
"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "loggingSidecar": {
                    "enabled": True,
                    "customConfig": True,
                    "airflowSidecarConfig": airflowSidecarConfig,
                },
            },
            show_only="templates/logging-sidecar-configmap.yaml",
        )
        assert len(docs) == 1
        doc = docs[0]
        assert "ConfigMap" == doc["kind"]
        assert "v1" == doc["apiVersion"]
        assert (vc := yaml.safe_load(doc["data"]["vector-config.yaml"]))
        assert vc["sinks"]["out"]["type"] == "datadog"
