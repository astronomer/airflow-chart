# Git Sync Relay

Git Sync Relay acts as a git repo relay between an upstream git server and the airflow deployment namespace. It uses the [kubernetes/git-sync](https://github.com/kubernetes/git-sync) sidecar to fetch a repo, and an additional container to expose this repo to the local namespace.

<img src="./git-sync-relay.svg">

## Configuration

In your helm values.yaml file, set values similar to these:

```yaml
gitSyncRelay:
  enabled: True

  repo:
    url: https://github.com/astronomer/airflow-example-dags
    branch: main
    depth: 1 # default to a shallow clone because it is faster, though it sacrifices git history
    wait: 60 # seconds between synchronizations with upstream git repo
    subPath: dags # if your dags dir is not the repo root, specify the path relative to the repo root
```
