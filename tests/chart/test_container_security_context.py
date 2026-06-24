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
