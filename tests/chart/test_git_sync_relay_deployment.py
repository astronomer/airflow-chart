import pytest

from tests import git_root_dir, supported_k8s_versions
from tests.utils import get_containers_by_name, get_env_vars_dict
from tests.utils.chart import render_chart

readinessProbe = {"httpGet": {"initialDelaySeconds": 20, "periodSeconds": 20, "path": "/rhealthz", "port": 8080, "scheme": "HTTP"}}
livenessProbe = {"httpGet": {"initialDelaySeconds": 20, "periodSeconds": 20, "path": "/chealthz", "port": 8080, "scheme": "HTTP"}}


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayDeployment:
    def test_gsr_deployment_default(self, kube_version):
        """Test that no git-sync-relay templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only=[x.relative_to(git_root_dir) for x in (git_root_dir / "templates/git-sync-relay").glob("*")],
        )
        assert len(docs) == 0

    def test_gsr_deployment_gsr_enabled_with_defaults(self, kube_version):
        """Test that a valid deployment is rendered when git-sync-relay is enabled with defaults."""
        values = {"gitSyncRelay": {"enabled": True}}

        docs = render_chart(
            kube_version=kube_version,
            show_only=[
                "templates/git-sync-relay/git-sync-relay-deployment.yaml",
                "templates/git-sync-relay/git-sync-relay-pvc.yaml",
            ],
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 2
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
        assert c_by_name["git-daemon"]["image"].startswith("quay.io/astronomer/ap-git-daemon:")
        assert c_by_name["git-daemon"]["livenessProbe"]

        git_dameon_env = get_env_vars_dict(c_by_name["git-daemon"].get("env"))
        assert not git_dameon_env.get("GIT_SYNC_REPO_FETCH_MODE")
        assert not git_dameon_env.get("GIT_SYNC_WEBHOOK_SECRET")
        git_sync_env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert git_sync_env.get("GIT_SYNC_REPO_FETCH_MODE") == "poll"
        assert not git_sync_env.get("GIT_SYNC_WEBHOOK_SECRET")
        spec = docs[0]["spec"]["template"]["spec"]
        assert spec["nodeSelector"] == {}
        assert spec["affinity"] == {}
        assert spec["tolerations"] == []

    def test_gsr_deployment_gsr_repo_share_mode_volume(self, kube_version):
        """Test that a valid deployment is rendered when git-sync-relay is enabled with repoShareMode=shared_volume."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": "shared_volume",
                "volumeSync": {"storageClassName": "my-usb-thumb-drive"},
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only=[
                "templates/git-sync-relay/git-sync-relay-deployment.yaml",
                "templates/git-sync-relay/git-sync-relay-pvc.yaml",
            ],
            values=values,
        )
        assert len(docs) == 2
        deployment, pvc = docs if docs[0]["kind"] == "Deployment" else docs[::-1]
        assert deployment["kind"] == "Deployment"
        assert deployment["apiVersion"] == "apps/v1"
        assert deployment["metadata"]["name"] == "release-name-git-sync-relay"
        assert pvc["kind"] == "PersistentVolumeClaim"
        assert pvc["kind"] == "PersistentVolumeClaim"
        assert pvc["spec"]["storageClassName"] == "my-usb-thumb-drive"
        c_by_name = get_containers_by_name(deployment)
        assert not c_by_name.get("git-daemon")
        assert len(c_by_name) == 1
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")

    def test_gsr_deployment_with_ssh_credentials_and_known_hosts(self, kube_version):
        """Test that a valid deployment is rendered when enabling git-sync with ssh credentials and known hosts and other custom configs."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "not-the-default-url",
                    "branch": "not-the-default-branch",
                    "depth": 22,
                    "wait": 333,
                    "subPath": "not-the-default-subPath",
                    "sshPrivateKeySecretName": "a-custom-secret-name",
                    "knownHosts": "not-the-default-knownHosts",
                },
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 2
        assert doc["spec"]["template"]["spec"]["volumes"] == [
            {"name": "git-sync-home", "emptyDir": {}},
            {"name": "git-repo-contents", "emptyDir": {}},
            {"name": "git-secret", "secret": {"secretName": "a-custom-secret-name"}},
            {"name": "release-name-git-sync-config", "configMap": {"name": "release-name-git-sync-config"}},
            {"name": "tmp", "emptyDir": {}},
        ]
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
        assert c_by_name["git-daemon"]["image"].startswith("quay.io/astronomer/ap-git-daemon:")
        assert c_by_name["git-sync"]["volumeMounts"] == [
            {"name": "git-sync-home", "mountPath": "/home/git-sync"},
            {"name": "git-secret", "mountPath": "/etc/git-secret/ssh", "readOnly": True, "subPath": "gitSshKey"},
            {
                "name": "release-name-git-sync-config",
                "mountPath": "/etc/git-secret/known_hosts",
                "readOnly": True,
                "subPath": "known_hosts",
            },
            {"name": "git-repo-contents", "mountPath": "/git"},
        ]
        assert get_env_vars_dict(c_by_name["git-sync"].get("env")) == {
            "GIT_SYNC_ROOT": "/git",
            "GIT_SYNC_REPO": "not-the-default-url",
            "GIT_SYNC_BRANCH": "not-the-default-branch",
            "GIT_SYNC_DEPTH": "22",
            "GIT_SYNC_WAIT": "333",
            "GIT_SYNC_SSH": "true",
            "GIT_SSH_KEY_FILE": "/etc/git-secret/ssh",
            "GIT_KNOWN_HOSTS": "true",
            "GIT_SSH_KNOWN_HOSTS_FILE": "/etc/git-secret/known_hosts",
            "GIT_SYNC_REPO_FETCH_MODE": "poll",
        }
        assert c_by_name["git-daemon"]["livenessProbe"]

    def test_gsr_deployment_without_ssh_credentials_and_known_hosts(self, kube_version):
        """Test that a valid deployment is rendered when enabling git-sync without ssh credentials."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "url": "not-the-default-url",
                    "branch": "not-the-default-branch",
                    "depth": 22,
                    "wait": 333,
                    "subPath": "not-the-default-subPath",
                },
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 2
        assert doc["spec"]["template"]["spec"]["volumes"] == [
            {"name": "git-sync-home", "emptyDir": {}},
            {"name": "git-repo-contents", "emptyDir": {}},
            {"name": "release-name-git-sync-config", "configMap": {"name": "release-name-git-sync-config"}},
            {"name": "tmp", "emptyDir": {}},
        ]
        assert c_by_name["git-sync"]["image"].startswith("quay.io/astronomer/ap-git-sync-relay:")
        assert c_by_name["git-daemon"]["image"].startswith("quay.io/astronomer/ap-git-daemon:")
        assert c_by_name["git-sync"]["volumeMounts"] == [
            {"name": "git-sync-home", "mountPath": "/home/git-sync"},
            {"name": "git-repo-contents", "mountPath": "/git"},
        ]
        assert get_env_vars_dict(c_by_name["git-sync"].get("env")) == {
            "GIT_SYNC_ROOT": "/git",
            "GIT_SYNC_REPO": "not-the-default-url",
            "GIT_SYNC_BRANCH": "not-the-default-branch",
            "GIT_SYNC_DEPTH": "22",
            "GIT_SYNC_WAIT": "333",
            "GIT_SYNC_REPO_FETCH_MODE": "poll",
        }
        assert c_by_name["git-daemon"]["livenessProbe"]

    def test_gsr_deployment_with_resource_overrides(self, kube_version):
        """Test that gitsync relay deployment are configurable with custom resource limits."""
        resources = {
            "requests": {"cpu": 99.5, "memory": "777Mi"},
            "limits": {"cpu": 99.6, "memory": "888Mi"},
        }
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "gitSync": {"resources": resources},
                "gitDaemon": {"resources": resources},
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        assert c_by_name["git-sync"]["resources"] == resources
        assert c_by_name["git-daemon"]["resources"] == resources

    def test_gsr_deployment_with_securitycontext_overrides(self, kube_version):
        """Test that gitsync  deployment are configurable with custom securitycontext."""
        gsrsecuritycontext = {"runAsUser": 12345, "privileged": True}
        values = {"gitSyncRelay": {"enabled": True, "securityContext": gsrsecuritycontext}}

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        assert gsrsecuritycontext == doc["spec"]["template"]["spec"]["securityContext"]

    def test_gsr_deployment_with_custom_registry_secret(self, kube_version):
        """Test git-sync-relay deployment with custom registry secret."""
        values = {
            "airflow": {"registry": {"secretName": "gscsecret"}},
            "gitSyncRelay": {"enabled": True},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        assert [{"name": "gscsecret"}] == doc["spec"]["template"]["spec"]["imagePullSecrets"]

    def test_gsr_deployment_with_custom_probes(self, kube_version):
        """Test git-sync-relay deployment with custom liveness and readiness probes."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "gitSync": {"readinessProbe": readinessProbe, "livenessProbe": livenessProbe},
                "gitDaemon": {"readinessProbe": readinessProbe, "livenessProbe": livenessProbe},
            }
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["apiVersion"] == "apps/v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        c_by_name = get_containers_by_name(doc)
        assert readinessProbe == c_by_name["git-daemon"]["readinessProbe"]
        assert livenessProbe == c_by_name["git-daemon"]["livenessProbe"]
        assert readinessProbe == c_by_name["git-sync"]["readinessProbe"]
        assert livenessProbe == c_by_name["git-sync"]["livenessProbe"]

    def test_gsr_deployment_with_repo_fetch_mode_webhook(self, kube_version):
        """Test git-sync-relay deployment with repoFetchMode=webhook."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoFetchMode": "webhook",
                "webhookSecretKey": "be sure to drink your ovaltine",
            },
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )

        assert len(docs) == 1
        c_by_name = get_containers_by_name(docs[0])
        assert len(c_by_name) == 2
        git_sync_env = get_env_vars_dict(c_by_name["git-sync"].get("env"))
        assert git_sync_env["GIT_SYNC_REPO_FETCH_MODE"] == "webhook"
        assert git_sync_env["GIT_SYNC_WEBHOOK_SECRET"] == "be sure to drink your ovaltine"
        git_dameon_env = get_env_vars_dict(c_by_name["git-daemon"].get("env"))
        assert not git_dameon_env.get("GIT_SYNC_REPO_FETCH_MODE")
        assert not git_dameon_env.get("GIT_SYNC_WEBHOOK_SECRET")

    def test_git_sync_server_deployment_with_sidecar_and_authproxy_enabled(self, kube_version):
        """Test git sync server deployment with sidecar components."""
        values = {
            "gitSyncRelay": {"enabled": True, "repoFetchMode": "webhook"},
            "loggingSidecar": {"enabled": True},
            "authSidecar": {"enabled": True},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        assert doc["spec"]["template"]["spec"]["volumes"] == [
            {"name": "git-sync-home", "emptyDir": {}},
            {"name": "git-repo-contents", "emptyDir": {}},
            {"name": "release-name-git-sync-config", "configMap": {"name": "release-name-git-sync-config"}},
            {"name": "config-volume", "configMap": {"name": "release-name-sidecar-config"}},
            {"name": "sidecar-logging-consumer", "emptyDir": {}},
            {"name": "nginx-sidecar-conf", "configMap": {"name": "release-name-git-sync-relay-nginx-conf"}},
            {"name": "nginx-cache", "emptyDir": {}},
            {"name": "tmp", "emptyDir": {}},
            {"name": "nginx-write-dir", "emptyDir": {}},
        ]

        c_by_name = get_containers_by_name(doc)
        assert len(c_by_name) == 4
        assert "git-sync" in c_by_name
        assert "git-daemon" in c_by_name
        assert "auth-proxy" in c_by_name
        assert "sidecar-log-consumer" in c_by_name
        assert c_by_name["git-sync"]["command"] == ["bash"]
        assert c_by_name["git-sync"]["args"] == [
            "-c",
            "/entrypoint.sh 1> >( tee -a /var/log/sidecar-logging-consumer/out.log ) 2> >( tee -a /var/log/sidecar-logging-consumer/err.log >&2 )",
        ]

        assert c_by_name["auth-proxy"]["volumeMounts"] == [
            {"mountPath": "/etc/nginx/nginx.conf", "name": "nginx-sidecar-conf", "subPath": "nginx.conf"},
            {"mountPath": "/var/cache/nginx", "name": "nginx-cache"},
            {"mountPath": "/tmp", "name": "tmp"},  # noqa: S108
            {"mountPath": "/var/lib/nginx/tmp", "name": "nginx-write-dir"},
        ]

    def test_git_sync_service_account_with_template(self, kube_version):
        """Test git-sync-relay service account with template."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "gitSyncRelay": {
                    "enabled": True,
                    "serviceAccount": {
                        "create": False,
                        "name": "custom-{{ .Release.Name }}-dag-processor",
                    },
                },
            },
            show_only=[
                "templates/git-sync-relay/git-sync-relay-deployment.yaml",
                "templates/git-sync-relay/git-sync-relay-serviceaccount.yaml",
            ],
        )
        assert len(docs) == 1
        service_accounts = [sa for sa in docs if sa.get("kind") == "ServiceAccount"]
        assert len(service_accounts) == 0
        doc = docs[0]
        assert doc["kind"] == "Deployment"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"

    def test_git_sync_relay_airflow_affinity(self, kube_version, airflow_node_pool_config):
        """Test that git sync relay global airflow affinity, node pool and toleration configs."""
        values = {
            "airflow": {
                "nodeSelector": airflow_node_pool_config["nodeSelector"],
                "affinity": airflow_node_pool_config["affinity"],
                "tolerations": airflow_node_pool_config["tolerations"],
            },
            "gitSyncRelay": {"enabled": True},
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        spec = docs[0]["spec"]["template"]["spec"]
        assert spec["affinity"] == airflow_node_pool_config["affinity"]
        assert spec["nodeSelector"] == airflow_node_pool_config["nodeSelector"]
        assert spec["tolerations"] == airflow_node_pool_config["tolerations"]

    def test_git_sync_relay_affinity(self, kube_version, airflow_node_pool_config):
        """Test that git sync relay affinity, node pool and toleration configs."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "nodeSelector": airflow_node_pool_config["nodeSelector"],
                "affinity": airflow_node_pool_config["affinity"],
                "tolerations": airflow_node_pool_config["tolerations"],
            },
        }

        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
            values=values,
        )
        assert len(docs) == 1
        spec = docs[0]["spec"]["template"]["spec"]
        assert spec["affinity"] == airflow_node_pool_config["affinity"]
        assert spec["nodeSelector"] == airflow_node_pool_config["nodeSelector"]
        assert spec["tolerations"] == airflow_node_pool_config["tolerations"]
