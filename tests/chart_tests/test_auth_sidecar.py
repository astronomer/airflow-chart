import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAuthSidecar:
    def test_auth_sidecar_config_defaults(self, kube_version):
        """Test logging sidecar config with defaults"""
        docs = render_chart(
            kube_version=kube_version,
            values={},
            show_only=[
                "templates/dag-deploy/dag-server-auth-sidecar-configmap.yaml",
                "templates/flower/flower-auth-sidecar-configmap.yaml",
                "templates/webserver/webserver-auth-sidecar-configmap.yaml",
            ],
        )
        assert len(docs) == 0

    def test_auth_sidecar_config_enabled(self, kube_version):
        """Test logging sidecar config with defaults"""
        docs = render_chart(
            kube_version=kube_version,
            values={"authSidecar": {"enabled": True}, "dagDeploy": {"enabled": True}},
            show_only=[
                "templates/dag-deploy/dag-server-auth-sidecar-configmap.yaml",
                "templates/flower/flower-auth-sidecar-configmap.yaml",
                "templates/webserver/webserver-auth-sidecar-configmap.yaml",
                "templates/dag-deploy/dag-server-statefulset.yaml",
            ],
        )
        assert len(docs) == 3
