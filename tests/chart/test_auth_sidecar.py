import pathlib

import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart

from . import get_containers_by_name


def common_pod_manager_test_cases(docs, docs_length, release_name, kind):
    """Test some things that should apply to all cases."""
    len(docs) == docs_length
    doc = docs[0]
    assert doc["kind"] == kind
    assert doc["apiVersion"] == "apps/v1"
    assert doc["metadata"]["name"] == release_name


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAuthSidecar:
    show_only = [
        "templates/dag-deploy/dag-server-auth-sidecar-configmap.yaml",
        "templates/flower/flower-auth-sidecar-configmap.yaml",
        "templates/webserver/webserver-auth-sidecar-configmap.yaml",
    ]

    def test_auth_sidecar_config_defaults(self, kube_version):
        """Test auth sidecar config with defaults"""
        docs = render_chart(kube_version=kube_version, values={}, show_only=self.show_only)
        assert len(docs) == 0

    def test_auth_sidecar_config_enabled_with_celeryexecutor(self, kube_version):
        """Test logging sidecar config with defaults"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "authSidecar": {"enabled": True},
                "dagDeploy": {"enabled": True},
                "airflow": {"executor": "CeleryExecutor"},
            },
            show_only=[
                "templates/dag-deploy/dag-server-auth-sidecar-configmap.yaml",
                "templates/webserver/webserver-auth-sidecar-configmap.yaml",
                "templates/flower/flower-auth-sidecar-configmap.yaml",
            ],
        )
        assert len(docs) == 3

    def test_auth_sidecar_config_enabled_with_kubernetesexecutor(self, kube_version):
        """Test logging sidecar config with defaults"""
        docs = render_chart(
            kube_version=kube_version,
            values={"authSidecar": {"enabled": True}, "dagDeploy": {"enabled": True}},
            show_only=[
                "templates/dag-deploy/dag-server-auth-sidecar-configmap.yaml",
                "templates/webserver/webserver-auth-sidecar-configmap.yaml",
                "templates/flower/flower-auth-sidecar-configmap.yaml",
            ],
        )
        assert len(docs) == 2

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
                "templates/dag-deploy/dag-server-auth-sidecar-configmap.yaml",
            ],
        )

        common_pod_manager_test_cases(docs, 3, "release-name-dag-server", "StatefulSet")
        c_by_name = get_containers_by_name(docs[0])
        assert c_by_name["auth-proxy"]["resources"] == resources
        assert volumeMounts in c_by_name["auth-proxy"]["volumeMounts"]

        assert docs[1]["kind"] == "Service"
        assert docs[1]["apiVersion"] == "v1"
        assert docs[1]["metadata"]["name"] == "release-name-dag-server"
        assert authSidecarServicePorts in docs[1]["spec"]["ports"]

        nginx_conf = pathlib.Path("tests/chart/test_data/dag-server-authsidecar-nginx.conf").read_text()
        assert nginx_conf in docs[2]["data"]["nginx.conf"]

    def test_auth_sidecar_security_context_with_dag_server_enabled(self, kube_version):
        """Test auth sidecar security context overrides"""
        securityContext = {
            "allowPrivilegeEscalation": False,
            "runAsNonRoot": True,
        }

        docs = render_chart(
            kube_version=kube_version,
            values={
                "authSidecar": {"enabled": True, "securityContext": securityContext},
                "dagDeploy": {"enabled": True},
            },
            show_only=[
                "templates/dag-deploy/dag-server-statefulset.yaml",
            ],
        )

        common_pod_manager_test_cases(docs, 1, "release-name-dag-server", "StatefulSet")
        c_by_name = get_containers_by_name(docs[0])
        assert c_by_name["auth-proxy"]["securityContext"] == securityContext

    def test_auth_sidecar_resources_with_dag_server_enabled(self, kube_version):
        """Test auth sidecar resource overrides"""
        resources = {
            "requests": {"cpu": 99.9, "memory": "777Mi"},
            "limits": {"cpu": 66.6, "memory": "888Mi"},
        }

        docs = render_chart(
            kube_version=kube_version,
            values={
                "authSidecar": {"enabled": True, "resources": resources},
                "dagDeploy": {"enabled": True},
            },
            show_only=[
                "templates/dag-deploy/dag-server-statefulset.yaml",
            ],
        )

        common_sts_test_cases(docs, 1, "release-name-dag-server", "StatefulSet")
        c_by_name = get_containers_by_name(docs[0])
        assert c_by_name["auth-proxy"]["resources"] == resources

    def test_auth_sidecar_config_with_git_sync_server_enabled(self, kube_version):
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
                "gitSyncRelay": {"enabled": True, "repoFetchMode": "webhook"},
                "authSidecar": {"enabled": True, "resources": resources},
            },
            show_only=[
                "templates/git-sync-relay/git-sync-relay-deployment.yaml",
                "templates/git-sync-relay/git-sync-relay-service.yaml",
                "templates/git-sync-relay/git-sync-relay-auth-sidecar-configmap.yaml",
            ],
        )

        common_sts_test_cases(docs, 3, "release-name-git-sync-relay", "Deployment")
        c_by_name = get_containers_by_name(docs[0])
        assert c_by_name["auth-proxy"]["resources"] == resources
        assert volumeMounts in c_by_name["auth-proxy"]["volumeMounts"]

        assert docs[1]["kind"] == "Service"
        assert docs[1]["apiVersion"] == "v1"
        assert docs[1]["metadata"]["name"] == "release-name-git-sync-relay"
        assert authSidecarServicePorts in docs[1]["spec"]["ports"]

        nginx_conf = pathlib.Path("tests/chart/test_data/git-sync-relay-authsidecar-nginx.conf").read_text()
        assert nginx_conf in docs[2]["data"]["nginx.conf"]
