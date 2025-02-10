from tests import git_root_dir
from tests.chart.helm_template_generator import render_chart


def test_gsr_pvc_defaults():
    """Test that no git-sync-relay pvc templates are rendered by default."""
    docs = render_chart(
        show_only=sorted([str(x.relative_to(git_root_dir)) for x in git_root_dir.rglob("*git-sync-relay-pvc*.yaml")]),
    )
    assert len(docs) == 0


def test_gsr_repo_share_mode_shared_volume():
    """Test that a git-sync-relay pvc template has the right contents when gitSyncRelay is enabled with shared_volume mode."""
    values = {
        "gitSyncRelay": {
            "enabled": True,
            "repoShareMode": "shared_volume",
        }
    }
    docs = render_chart(
        values=values,
        show_only=sorted([str(x.relative_to(git_root_dir)) for x in git_root_dir.rglob("*git-sync-relay-pvc*.yaml")]),
    )
    assert len(docs) == 1
    assert docs[0]["kind"] == "PersistentVolumeClaim"
    assert docs[0]["spec"]["accessModes"] == ["ReadWriteMany"]
    assert docs[0]["spec"]["resources"]["requests"]["storage"] == "10Gi"
    assert not docs[0]["spec"]["storageClassName"]
