import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions
from . import get_containers_by_name


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
            ],
        )
        assert len(docs) == 3

    def test_auth_sidecar_config_with_dag_server_enabled(self, kube_version):
        """Test logging sidecar config with defaults"""
        resources = {
            "requests": {"cpu": 99.9, "memory": "777Mi"},
            "limits": {"cpu": 66.6, "memory": "888Mi"},
        }
        volumeMounts = {
            "mountPath": "/etc/nginx/nginx.conf",
            "name": "nginx-sidecar-conf",
            "subPath": "nginx.conf",
        }

        authSidecarServicePorts = {
            "name": "auth-proxy",
            "port": 8084,
            "protocol": "TCP",
            "targetPort": 8084,
        }
        docs = render_chart(
            kube_version=kube_version,
            values={
                "authSidecar": {"enabled": True, "resources": resources},
                "dagDeploy": {"enabled": True},
            },
            show_only=[
                "templates/dag-deploy/dag-server-statefulset.yaml",
                "templates/dag-deploy/dag-server-service.yaml",
            ],
        )

        assert len(docs) == 2
        assert docs[0]["kind"] == "StatefulSet"
        assert docs[0]["apiVersion"] == "apps/v1"
        assert docs[0]["metadata"]["name"] == "release-name-dag-server"
        c_by_name = get_containers_by_name(docs[0])
        assert c_by_name["auth-proxy"]["resources"] == resources
        assert volumeMounts in c_by_name["auth-proxy"]["volumeMounts"]

        assert docs[1]["kind"] == "Service"
        assert docs[1]["apiVersion"] == "v1"
        assert docs[1]["metadata"]["name"] == "release-name-dag-server"
        assert authSidecarServicePorts in docs[1]["spec"]["ports"]
