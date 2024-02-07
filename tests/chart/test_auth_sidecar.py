import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAuthSidecar:
    show_only = [
        "templates/flower/flower-auth-sidecar-configmap.yaml",
        "templates/webserver/webserver-auth-sidecar-configmap.yaml",
    ]

    def test_auth_sidecar_config_defaults(self, kube_version):
        """Test logging sidecar config with defaults"""
        docs = render_chart(
            kube_version=kube_version, values={}, show_only=self.show_only
        )
        assert len(docs) == 0

    def test_auth_sidecar_config_enabled_with_celeryexecutor(self, kube_version):
        """Test logging sidecar config with defaults"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "authSidecar": {"enabled": True},
                "airflow": {"executor": "CeleryExecutor"},
            },
            show_only=[
                "templates/webserver/webserver-auth-sidecar-configmap.yaml",
                "templates/flower/flower-auth-sidecar-configmap.yaml",
            ],
        )
        assert len(docs) == 2

    def test_auth_sidecar_config_enabled_with_kubernetesexecutor(self, kube_version):
        """Test logging sidecar config with defaults"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "authSidecar": {"enabled": True},
                "airflow": {"executor": "KubernetesExecutor"},
            },
            show_only=[
                "templates/webserver/webserver-auth-sidecar-configmap.yaml",
                "templates/flower/flower-auth-sidecar-configmap.yaml",
            ],
        )
        assert len(docs) == 1
