"""Cross-cutting test for hardened container securityContext defaults.

Acceptance criteria: *every* container the chart renders must run with a
hardened container securityContext:

  - readOnlyRootFilesystem: true
  - allowPrivilegeEscalation: false
  - capabilities.drop: [ALL]

This renders the chart with all features enabled and reports every container
that does not meet the requirement, so newly-added containers are covered
automatically rather than being silently skipped.
"""

import pytest

from tests import supported_k8s_versions
from tests.utils import get_all_features, get_containers_by_name
from tests.utils.chart import render_chart

# The bundled postgresql is a test-only dependency, not something this chart ships.
EXCLUDED_DOCS = {"release-name-postgresql", "release-name-postgresql-hl"}


def hardening_problems(container: dict) -> dict:
    """Return the securityContext fields that are not hardened for a container.

    An empty dict means the container is fully hardened. Each entry maps the
    offending field to the (wrong) value actually found, so failures are
    actionable.
    """
    security_context = container.get("securityContext") or {}
    problems = {}
    if security_context.get("readOnlyRootFilesystem") is not True:
        problems["readOnlyRootFilesystem"] = security_context.get("readOnlyRootFilesystem")
    if security_context.get("allowPrivilegeEscalation") is not False:
        problems["allowPrivilegeEscalation"] = security_context.get("allowPrivilegeEscalation")
    drop = (security_context.get("capabilities") or {}).get("drop")
    if drop != ["ALL"]:
        problems["capabilities.drop"] = drop
    return problems


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
def test_all_containers_have_hardened_security_context(kube_version):
    """Render the whole chart and assert no container lacks the hardened securityContext."""
    docs = render_chart(kube_version=kube_version, values=get_all_features())

    offenders = {}
    for doc in docs:
        if doc.get("metadata", {}).get("name") in EXCLUDED_DOCS:
            continue
        owner = f"{doc['kind']}/{doc['metadata']['name']}"
        for name, container in get_containers_by_name(doc, include_init_containers=True).items():
            if problems := hardening_problems(container):
                offenders[f"{owner}:{name}"] = problems

    assert not offenders, "Containers without a hardened securityContext (field: actual value):\n" + "\n".join(
        f"  {key}: {value}" for key, value in sorted(offenders.items())
    )


# --- git-sync-relay PSS-Restricted conformance (PINF-585 follow-up) -----------------
#
# git-sync-relay is not processed by houston's securityHardeningConfig, so unlike
# redis/statsd/pgbouncer/gitSync its full restricted container set must come from the
# chart values. The cross-cutting test above only enforces the universal three-field
# floor; these tests additionally pin seccompProfile and the pod-level run-as-non-root
# behavior across both vanilla and OpenShift (PINF-559) modes.

GIT_SYNC_RELAY_DEPLOYMENT = "templates/git-sync-relay/git-sync-relay-deployment.yaml"

# Every git-sync-relay container must carry the full PSS-Restricted container securityContext.
RESTRICTED_CONTAINER_SECURITY_CONTEXT = {
    "readOnlyRootFilesystem": True,
    "allowPrivilegeEscalation": False,
    "capabilities": {"drop": ["ALL"]},
    "seccompProfile": {"type": "RuntimeDefault"},
}


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
@pytest.mark.parametrize("openshift_enabled", [False, True], ids=["vanilla", "openshift"])
def test_git_sync_relay_containers_are_pss_restricted(kube_version, openshift_enabled):
    """All three git-sync-relay containers carry the full PSS-Restricted container
    securityContext, in both vanilla and OpenShift modes."""
    docs = render_chart(
        kube_version=kube_version,
        values={
            "gitSyncRelay": {"enabled": True, "repoShareMode": "git_daemon"},
            "openshift": {"enabled": openshift_enabled},
        },
        show_only=[GIT_SYNC_RELAY_DEPLOYMENT],
    )
    assert len(docs) == 1
    containers = get_containers_by_name(docs[0], include_init_containers=True)
    # git-config-manager (init), git-sync, and the git-daemon sidecar (git_daemon mode).
    for name in ("git-config-manager", "git-sync", "git-daemon"):
        assert name in containers, f"expected '{name}' container in git-sync-relay deployment"
        assert containers[name]["securityContext"] == RESTRICTED_CONTAINER_SECURITY_CONTEXT


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
def test_git_sync_relay_pod_security_context_vanilla(kube_version):
    """Vanilla: the pod runs as non-root with the chart's UID/fsGroup."""
    docs = render_chart(
        kube_version=kube_version,
        values={"gitSyncRelay": {"enabled": True}, "openshift": {"enabled": False}},
        show_only=[GIT_SYNC_RELAY_DEPLOYMENT],
    )
    pod_security_context = docs[0]["spec"]["template"]["spec"]["securityContext"]
    assert pod_security_context == {"fsGroup": 65533, "runAsUser": 50000, "runAsNonRoot": True}


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
def test_git_sync_relay_pod_security_context_openshift(kube_version):
    """OpenShift (PINF-559): runAsUser/fsGroup are stripped for the restricted-v2 SCC,
    but runAsNonRoot is preserved."""
    docs = render_chart(
        kube_version=kube_version,
        values={"gitSyncRelay": {"enabled": True}, "openshift": {"enabled": True}},
        show_only=[GIT_SYNC_RELAY_DEPLOYMENT],
    )
    pod_security_context = docs[0]["spec"]["template"]["spec"]["securityContext"]
    assert pod_security_context == {"runAsNonRoot": True}
