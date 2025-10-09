import pytest

from tests import git_root_dir, supported_k8s_versions
from tests.utils.chart import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayServiceAccount:
    def test_gsr_defaults(self, kube_version):
        """Test that no git-sync-relay service templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only=sorted([str(x.relative_to(git_root_dir)) for x in git_root_dir.rglob("*git-sync-relay*.yaml")]),
        )
        assert len(docs) == 0

    def test_gsr_enabled_service_account(self, kube_version):
        """Test that a valid serviceAccount is rendered when git-sync-relay is enabled."""
        values = {"gitSyncRelay": {"enabled": True}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-serviceaccount.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "ServiceAccount"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"

    def test_gsr_server_annotations(self, kube_version):
        """Test that a valid serviceAccount is rendered with proper annotations
        when gsr is enabled and annotations are provided."""
        annotations = {"foo-key": "foo-value", "bar-key": "bar-value"}
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "serviceAccount": {"annotations": annotations},
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only=[
                "templates/git-sync-relay/git-sync-relay-serviceaccount.yaml",
                "templates/git-sync-relay/git-sync-relay-deployment.yaml",
            ],
            values=values,
        )
        assert len(docs) == 2
        doc = docs[0]
        assert doc["kind"] == "ServiceAccount"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        assert doc["metadata"]["annotations"] == annotations
        assert "release-name-git-sync-relay" == docs[1]["spec"]["template"]["spec"]["serviceAccountName"]

    def test_gsr_server_serviceaccount_overrides_defaults(self, kube_version):
        """Test that a serviceAccount overridable with disabled creation"""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "serviceAccount": {"create": False},
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only=[
                "templates/git-sync-relay/git-sync-relay-serviceaccount.yaml",
                "templates/git-sync-relay/git-sync-relay-deployment.yaml",
            ],
            values=values,
        )
        assert len(docs) == 1
        assert "default" == docs[0]["spec"]["template"]["spec"]["serviceAccountName"]

    def test_gsr_server_serviceaccount_overrides(self, kube_version):
        """Test that a serviceAccount overridable with disabled creation"""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "serviceAccount": {"create": False, "name": "git-sync-relay"},
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only=[
                "templates/git-sync-relay/git-sync-relay-serviceaccount.yaml",
                "templates/git-sync-relay/git-sync-relay-deployment.yaml",
            ],
            values=values,
        )
        assert len(docs) == 1
        assert "git-sync-relay" == docs[0]["spec"]["template"]["spec"]["serviceAccountName"]
