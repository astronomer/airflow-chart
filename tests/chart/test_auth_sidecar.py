import pathlib

import pytest

from tests import supported_k8s_versions
from tests.utils import get_containers_by_name
from tests.utils.chart import render_chart


def common_pod_manager_test_cases(docs, docs_length, release_name, kind):
    """Test some things that should apply to all apps/v1 pod managers."""
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
        "templates/api-server/api-server-auth-sidecar-configmap.yaml",
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

    def test_auth_sidecar_config_enabled_with_airflow3_apiserver(self, kube_version):
        """Test auth sidecar config with Airflow 3.x API server"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "authSidecar": {"enabled": True},
                "airflow": {"airflowVersion": "3.0.0"},
                "platform": {"houstonAuthServiceEndpointUrl": "https://houston./v1/authorization"},
            },
            show_only=[
                "templates/api-server/api-server-auth-sidecar-configmap.yaml",
            ],
        )
        assert len(docs) == 1

        doc = docs[0]
        assert doc["kind"] == "ConfigMap"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "release-name-api-server-nginx-conf"
        assert doc["metadata"]["labels"]["component"] == "api-server"
        assert "nginx.conf" in doc["data"]

        nginx_conf = pathlib.Path("tests/chart/test_data/api-server-authsidecar-nginx.conf").read_text()
        assert nginx_conf in docs[0]["data"]["nginx.conf"]

    def test_auth_sidecar_config_not_enabled_with_airflow2_apiserver(self, kube_version):
        """Test auth sidecar config is not generated for Airflow 2.x"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "authSidecar": {"enabled": True},
                "airflow": {"airflowVersion": "2.9.0"},
            },
            show_only=[
                "templates/api-server/api-server-auth-sidecar-configmap.yaml",
            ],
        )
        assert len(docs) == 0

    def test_webserver_auth_sidecar_config_not_enabled_with_airflow3(self, kube_version):
        """Test webserver auth sidecar config is not generated for Airflow 3.x"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "authSidecar": {"enabled": True},
                "airflow": {"airflowVersion": "3.0.0"},
            },
            show_only=[
                "templates/webserver/webserver-auth-sidecar-configmap.yaml",
            ],
        )
        assert len(docs) == 0

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
                "platform": {"houstonAuthServiceEndpointUrl": "https://houston./v1/authorization"},
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
            "blahBlah": "kitty cat",
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
        assert c_by_name["auth-proxy"]["securityContext"] == {**securityContext, "readOnlyRootFilesystem": True}

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

        common_pod_manager_test_cases(docs, 1, "release-name-dag-server", "StatefulSet")
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

        common_pod_manager_test_cases(docs, 3, "release-name-git-sync-relay", "Deployment")
        c_by_name = get_containers_by_name(docs[0])
        assert c_by_name["auth-proxy"]["resources"] == resources
        assert volumeMounts in c_by_name["auth-proxy"]["volumeMounts"]

        assert docs[1]["kind"] == "Service"
        assert docs[1]["apiVersion"] == "v1"
        assert docs[1]["metadata"]["name"] == "release-name-git-sync-relay"
        assert authSidecarServicePorts in docs[1]["spec"]["ports"]

        nginx_conf = pathlib.Path("tests/chart/test_data/git-sync-relay-authsidecar-nginx.conf").read_text()
        assert nginx_conf in docs[2]["data"]["nginx.conf"]
