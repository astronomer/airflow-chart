---
name: functional-tests
description: Use when writing, editing, reviewing, or running functional (end-to-end) tests for the Astronomer airflow-chart repository. Covers the kind-cluster workflow, testinfra pod fixtures, environment variables, and test organization.
---

# Functional Test Writing Guide

## Overview

Functional tests run against a live Kubernetes cluster (kind) with the chart installed. Unlike chart tests (which only render templates), they verify real runtime behavior: that binaries are on `PATH`, that the right pip packages and versions are installed in the Airflow image, that the Airflow CLI can manage connections/variables, that a DAG can be triggered and runs to success, and that the statsd config is the Astronomer one.

All functional tests live in a single file: `tests/functional/test_chart.py`. They use [testinfra](https://testinfra.readthedocs.io/) to `exec` into running containers via the `kubectl://` backend.

---

## Critical Rules

1. **A cluster must be running with the chart installed** before tests can pass — use `bin/reset-local-dev` (quick) or `bin/run-ci` (full CI flow).
2. **The `NAMESPACE` env var selects the namespace** the fixtures look in; it defaults to `airflow` when unset.
3. **Run tests through the project's managed environment** — `uv run pytest`, `.venv/bin/python -m pytest`, and `.venv/bin/pytest` are all valid (CI builds its own temp venv from `tests/requirements.txt`). Don't hand-roll a separate venv with `pip install`.
4. **There is one installation** (no unified/control/data scenarios) — everything is deployed into the `airflow` namespace.

---

## Local Setup Workflow

```bash
# 1. Build a fresh cluster and deploy the chart into the `airflow` namespace.
#    reset-local-dev -> bin/clean-slate (helm dep update, delete old kind cluster,
#    bin/start-kind-cluster) -> helm install.
bin/reset-local-dev           # honors $EXECUTOR, defaults to CeleryExecutor

# 2. Run the functional tests against the running cluster
export NAMESPACE=airflow
uv run pytest tests/functional/ -v
```

`bin/reset-local-dev` does a plain `helm install` suitable for iterating — it creates the cluster for you, so there is no separate cluster-creation step. The underlying `bin/start-kind-cluster` honors `$KUBE_VERSION` (default `1.31.6`) for the `kindest/node` image and creates the `airflow` namespace.

For a faithful reproduction of CI — building the `example_project` image, loading it into kind, enabling pgbouncer, waiting for all pods to become ready, exporting `NAMESPACE`/`SCHEDULER_POD`/`WEBSERVER_POD`, and running the suite — use:

```bash
bin/run-ci                    # honors $EXECUTOR and $HELM_CHART_PATH
```

**Choosing an executor** (matters for which pods exist — e.g. workers/flower only exist for CeleryExecutor):

```bash
export EXECUTOR=KubernetesExecutor   # or CeleryExecutor (default), LocalExecutor
```

---

## Environment Variables

The fixtures and tests read these (set by `bin/run-ci`, or set them yourself when running ad hoc):

| Variable          | Default          | Used for                                                      |
| ----------------- | ---------------- | ------------------------------------------------------------- |
| `NAMESPACE`       | `airflow`        | Namespace the pod fixtures search                             |
| `EXECUTOR`        | `CeleryExecutor` | Which Airflow executor to deploy                              |
| `SCHEDULER_POD`   | _(unset)_        | Pod name used when dumping scheduler logs on a failed DAG run |
| `WEBSERVER_POD`   | _(unset)_        | Exported by `bin/run-ci` for debugging                        |
| `HELM_CHART_PATH` | repo root        | Chart path `bin/run-ci` installs                              |

---

## Test Organization

```
tests/functional/
└── test_chart.py        # All functional tests + their pod fixtures
```

Tests and the fixtures they depend on currently live together in `test_chart.py`. If the file grows enough to warrant splitting, move the shared pod fixtures into a `tests/functional/conftest.py` first, then split tests by concern — but keep everything under `tests/functional/`.

---

## Pod Fixtures

Each fixture resolves a pod by the label selector `component=<name>` in `$NAMESPACE` (falling back to `airflow`), asserts at least one such pod exists, and yields a testinfra host bound to the relevant container via the `kubectl://` backend. They are `scope="session"`.

| Fixture         | Selector / container  | Notes                                                |
| --------------- | --------------------- | ---------------------------------------------------- |
| `webserver`     | `component=webserver` | The Airflow webserver/UI container                   |
| `scheduler`     | `component=scheduler` | The scheduler container                              |
| `triggerer`     | `component=triggerer` | The triggerer container                              |
| `statsd`        | `component=statsd`    | The statsd-exporter container                        |
| `docker_client` | —                     | A `docker.from_env()` client, for image-level checks |

To add a fixture for another component, copy the existing pattern:

```python
@pytest.fixture(scope="session")
def worker():
    """worker pod fixture."""
    if not (namespace := os.environ.get("NAMESPACE")):
        print("NAMESPACE env var is not present, using 'airflow' namespace")
        namespace = "airflow"
    kube = create_kube_client()
    pods = kube.list_namespaced_pod(namespace, label_selector="component=worker")
    assert len(pods.items) > 0, "Expected to find at least one pod with label 'component: worker'"
    pod = pods.items[0]
    yield testinfra.get_host(f"kubectl://{pod.metadata.name}?container=worker&namespace={namespace}")
```

`create_kube_client()` (defined in `test_chart.py`) loads kubeconfig via `config.load_kube_config()` and returns a `CoreV1Api`.

---

## Writing Tests

### Assert a binary is on PATH

```python
def test_airflow_in_path(webserver):
    """Ensure Airflow is in PATH"""
    assert webserver.exists("airflow"), "Expected 'airflow' to be in PATH"
```

### Assert a file exists

```python
def test_entrypoint(webserver):
    assert webserver.file("/entrypoint").exists, "Expected to find /entrypoint"
```

### Assert an installed pip package version

```python
from packaging.version import parse as semantic_version

def test_redis_version(webserver):
    redis_module = webserver.pip.get_packages()["redis"]
    version = redis_module["version"]
    assert semantic_version(version) != semantic_version("3.4.0"), "redis module must not be 3.4.0"
```

### Run Airflow CLI commands

```python
def test_airflow_variables(scheduler):
    """Test Variables can be added, retrieved and deleted"""
    assert "" in scheduler.check_output("airflow variables set test_key test_value")
    assert "test_value" in scheduler.check_output("airflow variables get test_key")
    assert "" in scheduler.check_output("airflow variables delete test_key")
```

`check_output` accepts printf-style args that testinfra quotes safely:

```python
scheduler.check_output("airflow connections add --conn-uri %s %s", test_conn_uri, test_conn_id)
```

### Inspect container config / image labels

```python
def test_statsd(statsd):
    """Check statsd pod is using the Astronomer statsd config."""
    statsd_config = statsd.check_output("cat /etc/statsd-exporter/mappings.yml")
    assert "Licensed to the Apache Software Foundation" not in statsd_config
    assert "action: drop" in statsd_config
```

---

## Eventually-Consistent State

Some behavior (a DAG running to success, a pod becoming reachable) is not instantaneous. The existing DAG-trigger test polls `airflow dags state ...` in a loop with a timeout and dumps scheduler logs (via `kubectl logs $SCHEDULER_POD`) on failure. When you need to wait for convergence, prefer either:

- a bounded poll loop with a clear timeout (as `test_airflow_trigger_dags` does), or
- `@pytest.mark.flaky(reruns=N, reruns_delay=S)` for genuinely flaky reachability checks.

Use waiting/retries sparingly — only when the cluster genuinely needs time to converge.

---

## What NOT to Do

- Do **not** assume pods exist for every executor — workers and flower only exist under `CeleryExecutor`; gate or skip accordingly.
- Do **not** hardcode the namespace — read `os.environ.get("NAMESPACE")` and fall back to `airflow`, matching the existing fixtures.
- Do **not** hand-roll a separate venv with `pip install`; run through the repo's managed environment (`uv run pytest tests/functional/` or `.venv/bin/pytest tests/functional/`).
- Do **not** add APC-style scenario directories (`unified/`, `control/`, `data/`) — this chart has a single installation.
