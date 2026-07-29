---
name: chart-tests
description: Use when writing, editing, reviewing, or running Helm chart tests for the Astronomer airflow-chart repository. Covers pytest patterns, render_chart() usage, sub-chart value nesting under `airflow`, parametrized tests, uv run commands, schema validation, and test organization.
---

# Chart Test Writing Guide

## Critical Rules

1. **Run tests through the project's managed environment** — `make unittest-chart`, `uv run pytest`, `.venv/bin/python -m pytest`, and `.venv/bin/pytest` are all valid. Don't hand-roll a separate venv with `pip install`.
2. **Parent-chart values are top-level; sub-chart values MUST be nested under `airflow`** (see [Parent-chart values vs. sub-chart values](#parent-chart-values-vs-sub-chart-values--critical))
3. **No `helm unittest` plugin** — all tests are pytest-based using `render_chart()`

---

## Test Organization

```
tests/
├── __init__.py               # supported_k8s_versions, newest/oldest_supported_kube_version, etc.
├── chart/                    # Helm template rendering tests (main focus)
│   ├── test_<component>.py   # One file per component
│   ├── conftest.py           # Shared fixtures (helm dep upgrade, docker client, node-pool config)
│   ├── __init__.py           # get_service_ports_by_name(), get_all_features()
│   └── test_data/            # Feature configs, expected outputs (e.g. auth-sidecar nginx confs)
├── functional/               # End-to-end cluster tests (testinfra) — see functional-tests skill
├── k8s_schema/               # Cached Kubernetes API schemas (v<version>-standalone/)
├── enable_all_features.yaml  # Values dict loaded by get_all_features()
└── utils/
    ├── chart.py              # render_chart() and k8s schema validation
    └── __init__.py           # get_containers_by_name(), get_all_features(), get_env_vars_dict(), get_pod_template()
```

---

## Writing Tests

### Basic Pattern

```python
import pytest
from tests import supported_k8s_versions
from tests.utils.chart import render_chart

DEPLOYMENT_FILE = "templates/dag-deploy/dag-server-statefulset.yaml"


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
def test_some_feature(kube_version):
    """Brief description of what is being tested."""
    docs = render_chart(
        kube_version=kube_version,
        show_only=[DEPLOYMENT_FILE],
        values={"dagDeploy": {"enabled": True}},
    )
    assert len(docs) == 1
    assert docs[0]["kind"] == "StatefulSet"
```

### Parent-chart values vs. sub-chart values — CRITICAL

This is an umbrella (parent) chart. There are two kinds of values:

**1. The parent chart's own values** — used by templates under top-level `templates/`. These are set at the top level of `values.yaml`: `dagDeploy`, `gitSyncRelay`, `authSidecar`, `loggingSidecar`, `extraObjects`, `ingress`, `sccEnabled`, `platform`, etc. Set them directly:

```python
values = {"dagDeploy": {"enabled": True}}
values = {"gitSyncRelay": {"enabled": True, "repo": {"url": "..."}}}
values = {"authSidecar": {"enabled": True}}
```

**2. The bundled Airflow sub-chart's values** — used by templates under `charts/airflow/templates/`. These **must** be nested under the `airflow` key:

```python
# ❌ WRONG — will not override the airflow sub-chart's values
values = {"pgbouncer": {"enabled": True}}

# ✅ CORRECT — nest under the `airflow` sub-chart key
values = {"airflow": {"pgbouncer": {"enabled": True}}}

# ✅ EXAMPLE — set the executor on the airflow sub-chart
docs = render_chart(
    values={"airflow": {"executor": "KubernetesExecutor"}},
    show_only=["charts/airflow/templates/scheduler/scheduler-deployment.yaml"],
)
```

### Using `show_only`

Always use `show_only` to target the specific template being tested. Parent-chart templates use the `templates/` prefix; sub-chart templates use the `charts/airflow/templates/` prefix:

```python
docs = render_chart(
    show_only=[
        "templates/git-sync-relay/git-sync-relay-deployment.yaml",
        "templates/dag-deploy/dag-server-service.yaml",
    ]
)
```

### Parametrized Tests

Always parametrize over `supported_k8s_versions` and over relevant values axes:

```python
@pytest.mark.parametrize("kube_version", supported_k8s_versions)
@pytest.mark.parametrize("enabled,docs_count", [(True, 1), (False, 0)])
def test_deployment_should_render(kube_version, enabled, docs_count):
    docs = render_chart(
        kube_version=kube_version,
        show_only=[DEPLOYMENT_FILE],
        values={"dagDeploy": {"enabled": enabled}},
    )
    assert len(docs) == docs_count
```

### Testing with All Features Enabled

`get_all_features()` loads `tests/enable_all_features.yaml`, which enables as many compatible features as possible. Not all features can be enabled simultaneously due to incompatibilities. When adding a new feature, enable it in `tests/enable_all_features.yaml` so it is exercised by the broad rendering tests in `test_default_chart.py` (e.g. the `readOnlyRootFilesystem` checks).

```python
from tests.utils import get_all_features

def test_with_all_features():
    docs = render_chart(values=get_all_features())
    kinds = [doc["kind"] for doc in docs]
    assert "Deployment" in kinds
```

---

## ConfigMap Scripts

Scripts embedded in ConfigMaps must follow these conventions:

1. **Static content only** — scripts must not use Helm templating to conditionally modify their content based on chart values. The rendered output must be identical regardless of what values are passed.

2. **Environment variable inputs** — all runtime configuration must be passed as environment variables defined in the container spec (via `env` or `envFrom`), not baked into the script at render time.

3. **Stored as files on disk** — scripts must be committed as real files in the repository (e.g. under `files/`) so they can be linted and reviewed like any other source file.

4. **Included via `.Files.Get`** — scripts must be included in ConfigMap templates using `.Files.Get`, not inline Helm template blocks:

   ```yaml
   # ✅ CORRECT
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: {{ include "chart.fullname" . }}-scripts
   data:
     my-script.sh: {{ .Files.Get "files/my-script.sh" | quote }}
   ```

   ```yaml
   # ❌ WRONG — inline script with template logic
   data:
     my-script.sh: |
       #!/bin/sh
       {{- if .Values.someFlag }}
       do_something
       {{- end }}
   ```

---

## Test Utilities

### `render_chart(values, show_only, kube_version, validate_objects)`

Renders the chart via `helm template` and returns parsed YAML documents.

| Parameter          | Type        | Description                                   |
| ------------------ | ----------- | --------------------------------------------- |
| `values`           | `dict`      | Values merged with chart defaults             |
| `show_only`        | `list[str]` | Templates to render (filters output)          |
| `kube_version`     | `str`       | K8s version for schema validation             |
| `validate_objects` | `bool`      | Validate against K8s schemas (default `True`) |

```python
from tests.utils.chart import render_chart

docs = render_chart(
    values={"gitSyncRelay": {"enabled": True}},
    show_only=["templates/git-sync-relay/git-sync-relay-service.yaml"],
    kube_version="1.31.0",
)
```

`render_chart` also accepts `name` (release name, default `release-name`), `namespace`, `baseDomain` (default `example.com`, set as `global.baseDomain`), and `lint_yaml` (run yamllint on the rendered output).

### `get_containers_by_name(doc, *, include_init_containers=False)`

Returns `{name: container_dict}` for all containers in a pod manager doc (Deployment, StatefulSet, DaemonSet, Job, CronJob). Pass `include_init_containers=True` to also include init containers.

```python
from tests.utils import get_containers_by_name

c_by_name = get_containers_by_name(doc, include_init_containers=True)
assert c_by_name["scheduler"]["securityContext"]["readOnlyRootFilesystem"]
assert c_by_name["git-sync-relay"]["securityContext"]["readOnlyRootFilesystem"]
```

### `get_all_features()`

Returns the values dict from `tests/enable_all_features.yaml` (most components enabled). Available from both `tests.utils` and `tests.chart`.

```python
from tests.utils import get_all_features
```

### Other utilities

In `tests/utils/__init__.py`:

- `get_env_vars_dict(container_env)` — converts an env list to a `{name: value}` dict
- `get_pod_template(doc)` — extracts the pod template from any pod manager (Deployment, StatefulSet, DaemonSet, Job, CronJob)

In `tests/chart/__init__.py`:

- `get_service_ports_by_name(doc)` — returns a Service's ports keyed by name

---

## Running Tests

The chart tests require the `airflow` sub-chart to be present in `charts/`. Run `make charts` (i.e. `helm dep update`) once before running tests, or use `make unittest-chart` which does it for you.

Any of these invocations work — `make unittest-chart` is the canonical full run; the others are for targeting specific tests once the venv exists (`make venv` / `uv sync` to create it):

### Correct examples

```bash
# Canonical full run via the Makefile (runs helm dep update + venv setup first)
make unittest-chart

# Pass extra pytest options to the Makefile target
make unittest-chart PYTEST_ADDOPTS='-v --maxfail=1 -k "git-sync"'

# Full suite in parallel (fastest — use for full runs). These are equivalent:
uv run pytest tests/chart/ -n auto --quiet
.venv/bin/python -m pytest tests/chart/ -n auto --quiet
.venv/bin/pytest tests/chart/ -n auto --quiet

# Single file
uv run pytest tests/chart/test_git_sync_relay_deployment.py --verbose

# Tests matching a pattern
uv run pytest tests/chart/ -k "pgbouncer" --verbose

# Single test
uv run pytest tests/chart/test_default_chart.py::TestDefaultChart::test_default_labels --verbose

# Verbose output, stop on first failure
uv run pytest tests/chart/ -vv --capture=no --maxfail=1

# Iterate on failures: re-run only last-failed tests
uv run pytest tests/chart/ --maxfail=1 --lf
```

> **Tip**: `-n auto` uses all CPU cores. Omit it when running a single file to avoid subprocess overhead.

### Incorrect examples

```bash
# ❌ WRONG — do not hand-roll a separate venv with pip. Use the repo's managed environment
# (make / uv / .venv) so dependencies match tests/requirements.txt and uv.lock.
python3 -m venv /tmp/myenv && /tmp/myenv/bin/pip install pytest && /tmp/myenv/bin/pytest tests/chart/
```

---

## Kubernetes Schema Validation

Tests validate rendered manifests against cached K8s OpenAPI schemas in `tests/k8s_schema/v<version>-standalone/`. Validation runs by default; missing schemas are fetched from the upstream `kubernetes-json-schema` repo and cached. Disable with `validate_objects=False`. The set of K8s versions is driven by `metadata.yaml` (`test_k8s_versions`) and exposed as `supported_k8s_versions` from `tests/__init__.py`.

```python
def test_statefulset_is_valid():
    docs = render_chart(
        values={"dagDeploy": {"enabled": True}},
        show_only=["templates/dag-deploy/dag-server-statefulset.yaml"],
        validate_objects=True,
    )
    assert docs[0]["kind"] == "StatefulSet"
```
