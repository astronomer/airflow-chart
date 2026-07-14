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
import yaml

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
    checked = 0
    for doc in docs:
        if doc.get("metadata", {}).get("name") in EXCLUDED_DOCS:
            continue
        owner = f"{doc['kind']}/{doc['metadata']['name']}"
        for name, container in get_containers_by_name(doc, include_init_containers=True).items():
            checked += 1
            if problems := hardening_problems(container):
                offenders[f"{owner}:{name}"] = problems

    # Guard against a render/enumeration regression that would make the assertion vacuous.
    assert checked, "No containers were rendered; cannot validate securityContext hardening"
    assert not offenders, "Containers without a hardened securityContext (field: actual value):\n" + "\n".join(
        f"  {key}: {value}" for key, value in sorted(offenders.items())
    )


# --- git-sync-relay PSS-Restricted conformance (PINF-585 follow-up) -----------------
#
# git-sync-relay is not processed by houston's securityHardeningConfig, so unlike
# redis/statsd/pgbouncer/gitSync its restricted set must come from the chart values. The
# cross-cutting test above only enforces the universal three-field container floor; these
# tests additionally pin the pod-level securityContext — runAsNonRoot and the seccompProfile
# (set pod-level to match the platform chart) — across both vanilla and OpenShift (PINF-559).

GIT_SYNC_RELAY_DEPLOYMENT = "templates/git-sync-relay/git-sync-relay-deployment.yaml"

# Every git-sync-relay container carries the restricted container securityContext.
# seccompProfile is set once at the pod level (not per-container) — see the pod tests below.
RESTRICTED_CONTAINER_SECURITY_CONTEXT = {
    "readOnlyRootFilesystem": True,
    "allowPrivilegeEscalation": False,
    "capabilities": {"drop": ["ALL"]},
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
    """Vanilla: the pod runs as non-root with the chart's UID/fsGroup and a seccomp profile."""
    docs = render_chart(
        kube_version=kube_version,
        values={"gitSyncRelay": {"enabled": True}, "openshift": {"enabled": False}},
        show_only=[GIT_SYNC_RELAY_DEPLOYMENT],
    )
    pod_security_context = docs[0]["spec"]["template"]["spec"]["securityContext"]
    assert pod_security_context == {
        "fsGroup": 65533,
        "runAsUser": 50000,
        "runAsNonRoot": True,
        "seccompProfile": {"type": "RuntimeDefault"},
    }


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
def test_git_sync_relay_pod_security_context_openshift(kube_version):
    """OpenShift (PINF-559): runAsUser/fsGroup are stripped for the restricted-v2 SCC,
    but runAsNonRoot and the seccomp profile are preserved."""
    docs = render_chart(
        kube_version=kube_version,
        values={"gitSyncRelay": {"enabled": True}, "openshift": {"enabled": True}},
        show_only=[GIT_SYNC_RELAY_DEPLOYMENT],
    )
    pod_security_context = docs[0]["spec"]["template"]["spec"]["securityContext"]
    assert pod_security_context == {
        "runAsNonRoot": True,
        "seccompProfile": {"type": "RuntimeDefault"},
    }


# --- dags.gitSync PSS-Restricted conformance (PINF-1024) ---------------------------
#
# dags.gitSync's git-sync/git-sync-init containers are rendered by the shared
# git_sync_container helper (in the vendored airflow subchart), whose securityContext
# resolves through localContainerSecurityContext. Unlike containerSecurityContext (used
# by the main airflow container), that helper has no fallback to the global
# Values.securityContexts.containers map that houston's securityHardeningConfig injects,
# and houston doesn't harden dags.gitSync directly either (PINF-1024) — so the restricted
# set must come entirely from this chart's values.yaml, same as git-sync-relay above.
# Overrides for the vendored "airflow" subchart's own top-level values (executor, dags, ...)
# must be nested under "airflow:" from this parent chart — see test_pod_template.py.
GIT_SYNC_RESTRICTED_CONTAINER_SECURITY_CONTEXT = {
    **RESTRICTED_CONTAINER_SECURITY_CONTEXT,
    "runAsNonRoot": True,
    "seccompProfile": {"type": "RuntimeDefault"},
}

# scheduler/triggerer/dag-processor always render (when enabled) regardless of executor choice.
# dag-processor also needs an explicit enable: with the chart's default airflowVersion (< 3.0.0)
# and dagProcessor.enabled unset, its deployment doesn't render at all (nil falls back to
# `semverCompare ">=3.0.0"`), independent of executor.
GIT_SYNC_ALWAYS_ON_DEPLOYMENTS = {
    "scheduler": ("charts/airflow/templates/scheduler/scheduler-deployment.yaml", {}),
    "triggerer": ("charts/airflow/templates/triggerer/triggerer-deployment.yaml", {}),
    "dag-processor": (
        "charts/airflow/templates/dag-processor/dag-processor-deployment.yaml",
        {"dagProcessor": {"enabled": True}},
    ),
}


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
@pytest.mark.parametrize("executor", ["CeleryExecutor", "KubernetesExecutor", "LocalExecutor"])
@pytest.mark.parametrize(
    "component,template_and_extra_values", GIT_SYNC_ALWAYS_ON_DEPLOYMENTS.items(), ids=GIT_SYNC_ALWAYS_ON_DEPLOYMENTS.keys()
)
def test_dags_git_sync_containers_are_pss_restricted(kube_version, executor, component, template_and_extra_values):
    """The git-sync and git-sync-init containers carry the full PSS-Restricted container
    securityContext on scheduler/triggerer/dag-processor, independent of executor choice."""
    template, extra_values = template_and_extra_values
    docs = render_chart(
        kube_version=kube_version,
        values={"airflow": {"executor": executor, "dags": {"gitSync": {"enabled": True}}, **extra_values}},
        show_only=[template],
    )
    assert len(docs) == 1
    containers = get_containers_by_name(docs[0], include_init_containers=True)
    for name in ("git-sync", "git-sync-init"):
        assert name in containers, f"expected '{name}' container in the {component} pod ({executor})"
        assert containers[name]["securityContext"] == GIT_SYNC_RESTRICTED_CONTAINER_SECURITY_CONTEXT


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
def test_dags_git_sync_celery_worker_containers_are_pss_restricted(kube_version):
    """CeleryExecutor's persistent worker Deployment (the pod type from the PINF-1024 bug
    report) renders its own git-sync containers via the same shared helper."""
    docs = render_chart(
        kube_version=kube_version,
        values={"airflow": {"executor": "CeleryExecutor", "dags": {"gitSync": {"enabled": True}}}},
        show_only=["charts/airflow/templates/workers/worker-deployment.yaml"],
    )
    assert len(docs) == 1
    containers = get_containers_by_name(docs[0], include_init_containers=True)
    for name in ("git-sync", "git-sync-init"):
        assert name in containers, f"expected '{name}' container in the worker pod"
        assert containers[name]["securityContext"] == GIT_SYNC_RESTRICTED_CONTAINER_SECURITY_CONTEXT


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
def test_dags_git_sync_kubernetes_executor_pod_template_is_pss_restricted(kube_version):
    """KubernetesExecutor has no persistent worker Deployment — each task pod is built from
    pod_template_file.yaml (embedded in the airflow ConfigMap), which renders a git-sync-init
    container via the same helper (only the init clone runs once per ephemeral task pod; the
    continuous-sync sidecar doesn't apply here) and must be hardened the same way."""
    docs = render_chart(
        kube_version=kube_version,
        values={"airflow": {"executor": "KubernetesExecutor", "dags": {"gitSync": {"enabled": True}}}},
        show_only="charts/airflow/templates/configmaps/configmap.yaml",
    )
    assert len(docs) == 1
    pod_template = yaml.safe_load(docs[0]["data"]["pod_template_file.yaml"])
    containers = {c["name"]: c for c in pod_template["spec"].get("containers", [])}
    containers.update({c["name"]: c for c in pod_template["spec"].get("initContainers", [])})
    assert "git-sync-init" in containers, "expected 'git-sync-init' container in the KubernetesExecutor pod template"
    assert containers["git-sync-init"]["securityContext"] == GIT_SYNC_RESTRICTED_CONTAINER_SECURITY_CONTEXT


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
def test_dags_git_sync_local_executor_has_no_separate_worker_pod(kube_version):
    """LocalExecutor runs tasks in-process in the scheduler, so there's no separate worker
    Deployment — and thus no separate git-sync containers — beyond what the scheduler pod
    already renders (covered by test_dags_git_sync_containers_are_pss_restricted above)."""
    docs = render_chart(
        kube_version=kube_version,
        values={"airflow": {"executor": "LocalExecutor", "dags": {"gitSync": {"enabled": True}}}},
        show_only="charts/airflow/templates/workers/worker-deployment.yaml",
    )
    assert docs == []


# --- Sidecar securityContext: enforced readOnlyRootFilesystem floor + null-safety --------
#
# auth_sidecar_container_spec and logging_sidecar_container_spec render their securityContext
# as `merge $required (.Values.<sidecar>.securityContext | default dict)`, where
# $required forces `readOnlyRootFilesystem: true`. Even when a user sets the override to null
# (or unsets it), the result must be the enforced `{readOnlyRootFilesystem: true}` floor —
# never `securityContext: null` and never dropping readOnlyRootFilesystem.
# Both containers render into the dag-server StatefulSet when their feature is enabled.
@pytest.mark.parametrize("kube_version", supported_k8s_versions)
@pytest.mark.parametrize(
    "component,container",
    [("authSidecar", "auth-proxy"), ("loggingSidecar", "sidecar-log-consumer")],
)
def test_sidecar_security_context_null_keeps_enforced_floor(kube_version, component, container):
    """A null/unset sidecar securityContext override still renders the enforced
    readOnlyRootFilesystem floor, not `null` and not an empty map."""
    docs = render_chart(
        kube_version=kube_version,
        values={"dagDeploy": {"enabled": True}, component: {"enabled": True, "securityContext": None}},
        show_only=["templates/dag-deploy/dag-server-statefulset.yaml"],
    )
    assert len(docs) == 1
    containers = get_containers_by_name(docs[0])
    assert container in containers, f"expected '{container}' container in the dag-server pod"
    security_context = containers[container]["securityContext"]
    assert security_context == {"readOnlyRootFilesystem": True}, (
        f"{container} securityContext should keep the enforced readOnlyRootFilesystem floor "
        f"when the override is null, got {security_context!r}"
    )
