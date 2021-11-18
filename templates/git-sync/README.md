# Git Sync

Git Sync acts as a git repo relay from an upstream git server to the airflow deployment namespace. It uses the [kubernetes/git-sync](https://github.com/kubernetes/git-sync) sidecar to fetch a repo, and an additional pod to expose this repo to the local namespace.
