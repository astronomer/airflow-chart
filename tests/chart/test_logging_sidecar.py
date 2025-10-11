import textwrap

import pytest
import yaml

from tests import supported_k8s_versions
from tests.utils.chart import render_chart


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

    def test_logging_sidecar_apiserver_filter(self, kube_version):
        """Test that api-server logs are properly filtered and processed"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "loggingSidecar": {"enabled": True},
            },
            show_only="templates/logging-sidecar-configmap.yaml",
        )
        assert len(docs) == 1
        vc = yaml.safe_load(docs[0]["data"]["vector-config.yaml"])

        assert "filter_apiserver_logs" in vc["transforms"]
        assert 'includes(["api-server"], .component)' in vc["transforms"]["filter_apiserver_logs"]["condition"]["source"]

        transform_remove_fields_inputs = vc["transforms"]["transform_remove_fields"]["inputs"]
        assert "filter_apiserver_logs" in transform_remove_fields_inputs

        transform_task_log_inputs = vc["transforms"]["transform_task_log"]["inputs"]
        assert "filter_apiserver_logs" not in transform_task_log_inputs

    def test_logging_sidecar_airflow3_support(self, kube_version):
        """Test logging sidecar config with Airflow 3.x changes"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "loggingSidecar": {"enabled": True},
                "airflow": {
                    "airflowVersion": "3.0.0",
                },
            },
            show_only="templates/logging-sidecar-configmap.yaml",
        )
        assert len(docs) == 1
        vc = yaml.safe_load(docs[0]["data"]["vector-config.yaml"])

        parse_airflow3_path = vc["transforms"]["parse_airflow3_path"]
        assert parse_airflow3_path["type"] == "remap"
        assert "airflow_log_files" in parse_airflow3_path["inputs"]

        assert "parsed_log = parse_json!(.message)" in parse_airflow3_path["source"]

        assert "dag_id" in parse_airflow3_path["source"]
        assert "task_id" in parse_airflow3_path["source"]
        assert "run_id" in parse_airflow3_path["source"]
        assert "map_index" in parse_airflow3_path["source"]
        assert "try_number" in parse_airflow3_path["source"]

        assert ".is_airflow3 = true" in parse_airflow3_path["source"]

        transform_airflow_logs = vc["transforms"]["transform_airflow_logs"]
        assert "parse_airflow3_path" in transform_airflow_logs["inputs"]

        transform_remove_fields = vc["transforms"]["transform_remove_fields"]
        assert "del(.is_airflow3)" in transform_remove_fields["source"]

        assert "del(.execution_date)" in transform_remove_fields["source"]
