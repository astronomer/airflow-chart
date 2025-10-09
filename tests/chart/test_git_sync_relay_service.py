import pytest

from tests import supported_k8s_versions
from tests.chart import get_service_ports_by_name
from tests.utils.chart import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestGitSyncRelayService:
    def test_gsr_service_default(self, kube_version):
        """Test that no git-sync-relay templates are rendered by default."""
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-service.yaml",
        )
        assert len(docs) == 0

    def test_gsr_service_gsr_enabled(self, kube_version):
        """Test that a valid service is rendered when git-sync-relay is enabled."""
        values = {"gitSyncRelay": {"enabled": True}}
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-service.yaml",
            values=values,
        )
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Service"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"

    @pytest.mark.parametrize("repoShareMode,", ["git_daemon", "shared_volume"])
    @pytest.mark.parametrize("repoFetchMode", ["poll", "webhook"])
    def test_gsr_service_gsr_enabled_configured_ports(self, kube_version, repoFetchMode, repoShareMode):
        """Test that a correct port list is rendered when git-sync-relay is configured with different modes."""
        values = {
            "gitSyncRelay": {
                "enabled": True,
                "repoShareMode": repoShareMode,
                "repoFetchMode": repoFetchMode,
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            show_only="templates/git-sync-relay/git-sync-relay-service.yaml",
            values=values,
        )
        if repoFetchMode == "poll" and repoShareMode == "shared_volume":
            assert len(docs) == 0
            return
        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "Service"
        assert doc["apiVersion"] == "v1"
        assert doc["metadata"]["name"] == "release-name-git-sync-relay"
        ports = get_service_ports_by_name(doc)
        if repoFetchMode == "webhook":
            assert ports["webhook"]["port"] == 8000
            assert ports["webhook"]["targetPort"] == 8000
            assert ports["webhook"]["protocol"] == "TCP"
        else:
            assert not ports.get("git-sync-relay")

        if repoShareMode == "git_daemon":
            assert ports["git"]["port"] == 9418
            assert ports["git"]["targetPort"] == 9418
            assert ports["git"]["protocol"] == "TCP"
        else:
            assert not ports.get("git")
