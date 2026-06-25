# CLAUDE.md

Guidance for Claude Code (and humans) working in the `airflow-chart` repo.

## What this chart is

This repo contains a single Helm **umbrella chart** — a parent chart that declares a
dependency (a _subchart_) and adds its own templates on top.

- **Parent chart:** named `airflow` (`Chart.yaml` → `name: airflow`). The repository is
  `airflow-chart`; the chart it contains is `airflow`.
- **Dependency / subchart:** the parent declares exactly one entry under `Chart.yaml`
  `dependencies:` — the upstream Astronomer Airflow chart, which is **also named `airflow`**.
  `helm dependency update` (aka `make charts`) fetches it into `charts/`.
- **The two `airflow`s are different charts.** "Parent `airflow`" = this repo's umbrella
  chart. "Subchart `airflow`" = the upstream chart it depends on. They share a name — that
  collision is the main thing to keep straight.

### How values reach each chart (Helm value scoping)

Helm routes any values nested under a top-level key that matches a subchart's name into
that subchart. Because the subchart is named `airflow`:

- Keys **under `airflow:`** in `values.yaml` configure the **subchart** (upstream Airflow) —
  e.g. `airflow.redis.*`, `airflow.pgbouncer.*`, `airflow.dags.gitSync.*`.
- **Top-level keys** (not under `airflow:`) configure the **parent chart's own resources** —
  e.g. `gitSyncRelay.*`, `dagDeploy.*`, `authSidecar.*`, `loggingSidecar.*`, `ingress.*`.

### Where templates live

- **Parent templates:** top-level `templates/` — Astronomer-specific resources layered on
  top of the subchart (git-sync-relay, dag-deploy server, auth/logging sidecars, ingress,
  OpenShift SCC, …).
- **Subchart templates:** `charts/airflow/templates/` (present after `make charts`) — the
  upstream chart. Do not edit these; they are a fetched dependency.

## Testing & CI

- Chart (render) tests: `make unittest-chart`, or `uv run pytest tests/chart/`. The tested
  Kubernetes versions come from `metadata.yaml`.
- Functional / e2e tests run in CircleCI against **kind** clusters, across the
  `CeleryExecutor`, `LocalExecutor`, and `KubernetesExecutor`.

> [!IMPORTANT] > **OpenShift is NOT exercised in CI.** CI runs only on kind (vanilla Kubernetes).
> OpenShift-specific behavior — e.g. the restricted-v2 SCC UID-range stripping in the
> `gitSyncRelay.podSecurityContext` helper (PINF-559), and anything gated on
> `openshift.enabled=true` — must be verified manually. **A change can be fully green in CI
> and still break only on OpenShift.**

## CI config

`.circleci/config.yml` is a generated file — edit `.circleci/config.yml.j2` and/or
`bin/generate_circleci_config.py`, then regenerate. Never edit `config.yml` directly. See
the `circleci` skill.
