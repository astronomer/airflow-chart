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

## Sharp edge: `authSidecar` / `loggingSidecar` are easy to miss in any pod-spec feature

Both are **top-level parent-chart keys** (see value scoping above) that add an extra container to a pod — but neither is defined inline in the pod template you'd naturally go looking at. They're rendered by shared helpers in `templates/_helpers.yaml`: `auth_sidecar_container_spec` (~line 406) and `logging_sidecar_container_spec` (~line 363), then `{{ include }}`'d into `templates/dag-deploy/dag-server-statefulset.yaml` and `templates/git-sync-relay/git-sync-relay-deployment.yaml`. Values defaults live at `values.yaml:692-746`.

**Why this bites people:** if you're adding or auditing a pod-spec feature (security context, resources, probes, env vars, volume mounts, labels, image/registry override, network policy, etc.) by reading `dag-server-statefulset.yaml` or `git-sync-relay-deployment.yaml` top to bottom, you will see the `{{ include "auth_sidecar_container_spec" . }}` / `{{ include "logging_sidecar_container_spec" . }}` lines, but the actual container spec — and therefore whatever field you're checking or adding — lives in `_helpers.yaml`, not the file you're looking at. Grepping the calling template for the field name (e.g. `resources:`) will miss it entirely.

**Concrete history:** this exact blind spot caused two rounds of missed coverage in the K8s Security Policy Compatibility project (`employment-astronomer` vault, `projects/2026-05-11-k8s-security-policy-compatibility/`) — first on startup probes (found 2026-07-08, fixed 2026-07-17 via PINF-951), then again on resource limits (`resources: {}` defaults for both helpers, found 2026-07-13, fixed 2026-07-17 via PINF-969 — both on this same branch).

**Rule of thumb:** when adding or auditing ANY chart-wide pod-spec convention, explicitly `grep -rn "authSidecar\|loggingSidecar\|auth_sidecar\|logging_sidecar"` in this repo (and its siblings — the astronomer platform chart has an unrelated, independently-implemented `global.authSidecar` copy-pasted into several platform components, and houston-api has a third, separately-implemented `authSideCar`/`extraContainers` injection onto rendered Airflow pods; note the inconsistent casing across all three — `authSidecar` here, `authSideCar` in houston-api). Don't assume a per-file audit caught it.

## Testing & CI

- Chart (render) tests: `make unittest-chart`, or `uv run pytest tests/chart/`. The tested
  Kubernetes versions come from `metadata.yaml`.
- Functional / e2e tests run in CircleCI against **kind** clusters, across the
  `CeleryExecutor`, `LocalExecutor`, and `KubernetesExecutor`.

**Important — OpenShift is NOT exercised in CI.** CI runs only on kind (vanilla Kubernetes). OpenShift-specific behavior — e.g. the restricted-v2 SCC UID-range stripping in the `gitSyncRelay.podSecurityContext` helper (PINF-559), and anything gated on `openshift.enabled=true` — must be verified manually. A change can be fully green in CI and still break only on OpenShift.

## CI config

`.circleci/config.yml` is a generated file — edit `.circleci/config.yml.j2` and/or
`bin/generate_circleci_config.py`, then regenerate. Never edit `config.yml` directly. See
the `circleci` skill.
