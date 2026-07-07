---
name: circleci
description: Use when writing, editing, or reviewing CircleCI configuration for the Astronomer airflow-chart repository. Covers script organization, inline vs external scripts, and config conventions.
---

# CircleCI Configuration Guide

## Critical Rules

1. **No long inline scripts** — script logic for any language must not be written inline in `.circleci/config.yml` if the script has complicated flow control. Complicated scripts belong in `bin/`.
2. **Scripts live in `bin/`** — every script called from CircleCI must exist as a file in the `bin/` directory with an appropriate extension (e.g. `bin/my-script.sh`, `bin/my-script.py`).
3. **Pin all versions** — never use `latest` or unpinned tags for Docker images or installed tools. Always specify an exact version to prevent supply chain vulnerabilities and ensure reproducible builds.

---

## Script Organization

Scripts invoked by CircleCI jobs must be committed to the repository under `bin/` so they can be:

- Linted and reviewed like any other source file
- Tested and run locally without needing CI
- Reused across multiple jobs or workflows

```yaml
# ✅ CORRECT — call a script from bin/
steps:
  - run:
      name: Build Helm chart
      command: bin/build-helm-chart.sh
```

```yaml
# ❌ WRONG — inline shell logic in the CircleCI config
steps:
  - run:
      name: Build Helm chart
      command: |
        helm package .
        mv airflow-*.tgz /tmp/chart/
```

---

## Config Generation Pipeline

`.circleci/config.yml` is **never edited directly** — it is a generated file (its header says so). It is produced by rendering the Jinja2 template `.circleci/config.yml.j2` via `bin/generate_circleci_config.py`:

```bash
# Regenerate config.yml from the template
bin/generate_circleci_config.py        # or: uv run bin/generate_circleci_config.py
```

The generator injects a small set of computed variables into the template at render time:

- `kube_versions` — read from `metadata.yaml` (`test_k8s_versions`)
- `executors` — `["CeleryExecutor", "LocalExecutor", "KubernetesExecutor"]`
- `machine_image_version` — the CircleCI machine image (pinned in the generator script)
- `ci_runner_version` — derived from the current year-month

Always edit `.circleci/config.yml.j2` (or `bin/generate_circleci_config.py` for the injected values), then regenerate and commit both the template and the generated `config.yml`. The chart's K8s test matrix is driven entirely by `metadata.yaml`, so adding/removing a tested Kubernetes version is a `metadata.yaml` edit followed by a regenerate.

> **CI runs only on kind (vanilla Kubernetes), never OpenShift.** The matrix is `kube_versions` × `executors` on kind. OpenShift-specific behavior (e.g. `openshift.enabled=true` SCC / UID-range handling, PINF-559) is **not** exercised in CI and must be verified manually — a change can be green in CI and still break only on OpenShift. See `CLAUDE.md`.

---

## Version Pinning

Always pin exact versions for Docker images and any tools installed during a job. Using `latest` or loose tags introduces supply chain risk and makes builds non-reproducible.

Pinned versions that the generator controls (e.g. `machine_image_version`) live in `bin/generate_circleci_config.py`, and the Kubernetes test versions live in `metadata.yaml` — keep them there rather than scattered inline so they are easy to audit and update in one place. Include a link near each version declaration to where released versions can be found, so updating doesn't require searching online.

```python
# ✅ CORRECT — version pinned in bin/generate_circleci_config.py
machine_image_version = "ubuntu-2204:2025.09.1"  # https://circleci.com/developer/machine/image/ubuntu-2204
```

```yaml
# ✅ CORRECT — version referenced via an injected variable in config.yml.j2
machine:
  image: { { machine_image_version } }
```

```yaml
# ❌ WRONG — unpinned image
docker:
  - image: cimg/python:latest
```

```yaml
# ✅ CORRECT — pinned tool version installed via a bin/ script
- run:
    name: Install CI tools
    command: bin/install-ci-tools

# ❌ WRONG — unversioned tool install piped straight from the internet
- run:
    name: Install helm
    command: curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```
