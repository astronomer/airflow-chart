from tests.utils.chart import render_chart

show_only = "templates/git-sync-relay/git-sync-relay-init-job.yaml"


def test_gsr_pvc_not_rendered_by_default():
    """Test that no git-sync-relay PVC is rendered by default."""
    docs = render_chart(show_only=show_only)
    assert len(docs) == 0


def test_gsr_pvc_rendered_with_shared_volume():
    """Test that the PVC hook has the right contents when gitSyncRelay is enabled with shared_volume mode."""
    values = {
        "gitSyncRelay": {
            "enabled": True,
            "repoShareMode": "shared_volume",
        }
    }
    docs = render_chart(values=values, show_only=show_only)
    pvc_docs = [d for d in docs if d["kind"] == "PersistentVolumeClaim"]
    assert len(pvc_docs) == 1
    pvc_doc = pvc_docs[0]
    assert pvc_doc["metadata"]["name"] == "git-repo-contents"
    assert pvc_doc["spec"]["accessModes"] == ["ReadWriteMany"]
    assert pvc_doc["spec"]["resources"]["requests"]["storage"] == "10Gi"
    assert not pvc_doc["spec"]["storageClassName"]
