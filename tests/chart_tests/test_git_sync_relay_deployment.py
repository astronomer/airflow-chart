import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayDeployment:
    def test_gsr_deployment_default(self, kube_version):
        """Test that no git-sync-relay templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-deployment.yaml",
        )
        assert len(docs) == 0

    def test_gsr_deployment_gsr_enabled(self, kube_version):
        """Test that a valid deployment is rendered when git-sync-relay is enabled."""
        values = {"gitSyncRelay": {"enabled": True}}

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
        c_by_name = {
            c["name"]: c for c in doc["spec"]["template"]["spec"]["containers"]
        }
        assert len(c_by_name) == 2
        assert c_by_name["git-sync"]["image"].startswith(
            "quay.io/astronomer/ap-git-sync:"
        )
        assert c_by_name["git-daemon"]["image"].startswith(
            "quay.io/astronomer/ap-git-daemon:"
        )

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
        c_by_name = {
            c["name"]: c for c in doc["spec"]["template"]["spec"]["containers"]
        }

        assert len(c_by_name) == 2
        assert doc["spec"]["template"]["spec"]["volumes"] == [
            {"name": "git-repo-contents", "emptyDir": {}},
            {
                "name": "git-secret",
                "secret": {"secretName": "a-custom-secret-name"},
            },
            {
                "name": "release-name-git-sync-config",
                "configMap": {"name": "release-name-git-sync-config"},
            },
        ]
        assert c_by_name["git-sync"]["image"].startswith(
            "quay.io/astronomer/ap-git-sync:"
        )
        assert c_by_name["git-daemon"]["image"].startswith(
            "quay.io/astronomer/ap-git-daemon:"
        )
        assert c_by_name["git-sync"]["volumeMounts"] == [
            {
                "name": "git-secret",
                "mountPath": "/etc/git-secret/ssh",
                "readOnly": True,
                "subPath": "gitSshKey",
            },
            {
                "name": "release-name-git-sync-config",
                "mountPath": "/etc/git-secret/known_hosts",
                "readOnly": True,
                "subPath": "known_hosts",
            },
            {"name": "git-repo-contents", "mountPath": "/git"},
        ]
        assert c_by_name["git-sync"]["env"] == [
            {"name": "GIT_ROOT", "value": "/git"},
            {"name": "GIT_SYNC_SSH", "value": "true"},
            {"name": "GIT_SSH_KEY_FILE", "value": "/etc/git-secret/ssh"},
            {"name": "GIT_KNOWN_HOSTS", "value": "true"},
            {
                "name": "GIT_SSH_KNOWN_HOSTS_FILE",
                "value": "/etc/git-secret/known_hosts",
            },
        ]
        assert c_by_name["git-sync"]["args"] == [
            "--repo=not-the-default-url",
            "--branch=not-the-default-branch",
            "--depth=22",
            "--wait=333",
            "--root=/git",
        ]

    def test_gsr_deployment_without_ssh_credentials_and_known_hosts(self, kube_version):
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
        c_by_name = {
            c["name"]: c for c in doc["spec"]["template"]["spec"]["containers"]
        }

        assert len(c_by_name) == 2
        assert doc["spec"]["template"]["spec"]["volumes"] == [
            {"name": "git-repo-contents", "emptyDir": {}},
            {
                "name": "release-name-git-sync-config",
                "configMap": {"name": "release-name-git-sync-config"},
            },
        ]
        assert c_by_name["git-sync"]["image"].startswith(
            "quay.io/astronomer/ap-git-sync:"
        )
        assert c_by_name["git-daemon"]["image"].startswith(
            "quay.io/astronomer/ap-git-daemon:"
        )
        assert c_by_name["git-sync"]["volumeMounts"] == [
            {"name": "git-repo-contents", "mountPath": "/git"},
        ]
        assert c_by_name["git-sync"]["env"] == [
            {"name": "GIT_ROOT", "value": "/git"},

        ]
        assert c_by_name["git-sync"]["args"] == [
            "--repo=not-the-default-url",
            "--branch=not-the-default-branch",
            "--depth=22",
            "--wait=333",
            "--root=/git",
        ]
