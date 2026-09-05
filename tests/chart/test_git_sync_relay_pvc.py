from tests.utils.chart import render_chart

show_only = "templates/git-sync-relay/git-sync-relay-init-job.yaml"
plain_pvc_template = "templates/git-sync-relay/git-sync-relay-pvc.yaml"


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


def test_gsr_plain_pvc_not_rendered_by_default():
    """The plain, non-hook PVC declaration (git-sync-relay-pvc.yaml) also renders nothing
    outside shared_volume mode."""
    docs = render_chart(show_only=plain_pvc_template)
    assert len(docs) == 0


def test_gsr_plain_pvc_rendered_with_shared_volume():
    """The plain PVC declaration keeps the PVC tracked as a normal release resource, not just
    a hook, so an existing shared_volume install's PVC is never at risk of being pruned on
    upgrade (see the template's own comment). Same spec as the hook-based PVC, no hook
    annotations of its own."""
    values = {
        "gitSyncRelay": {
            "enabled": True,
            "repoShareMode": "shared_volume",
        }
    }
    docs = render_chart(values=values, show_only=plain_pvc_template)
    assert len(docs) == 1
    pvc_doc = docs[0]
    assert pvc_doc["kind"] == "PersistentVolumeClaim"
    assert "annotations" not in pvc_doc["metadata"]
    assert pvc_doc["metadata"]["name"] == "git-repo-contents"
    assert pvc_doc["spec"]["accessModes"] == ["ReadWriteMany"]
    assert pvc_doc["spec"]["resources"]["requests"]["storage"] == "10Gi"
    assert not pvc_doc["spec"]["storageClassName"]
