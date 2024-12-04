import pytest

from tests import supported_k8s_versions
from tests.chart.helm_template_generator import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayConfigmap:
    def test_gsr_configmap_default(self, kube_version):
        """Test that no git-sync-relay templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-configmap.yaml",
        )
        assert len(docs) == 0

    def test_gsr_configmap_gsr_enabled(self, kube_version):
        """Test that valid configmaps are rendered when git-sync-relay is enabled."""
        values = {"gitSyncRelay": {"enabled": True}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-configmap.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]

        assert doc["kind"] == "ConfigMap"
        assert len(doc["data"]) == 1
        # ed25519 keys, and substrings of other key types
        key_lines = [
            "github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9",
            "github.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBEmKSENj",
            "github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl",
            "gitlab.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsj2bNKTBSpIYDEGk9KxsGh3mySTRgMtXL583qmBpz",
            "gitlab.com ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBFSMqzJe",
            "gitlab.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAfuCHKVTjquxvt6CM6tdG4SLp1Btn/nOeHHE5UOzRdf",
        ]
        assert all(x in doc["data"]["known_hosts"] for x in key_lines)

    def test_gsr_configmap_gsr_enabled_with_custom_known_hosts(self, kube_version):
        """Test that valid configmaps are rendered when git-sync-relay is enabled and has custom knownHosts."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repo": {
                    "knownHosts": "not-the-default-knownHosts",
                },
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-configmap.yaml",
            values=values,
        )
        assert len(docs) == 1
        assert docs[0]["data"] == {"known_hosts": "not-the-default-knownHosts\n"}
