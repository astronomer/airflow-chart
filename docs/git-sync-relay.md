# Git Sync Relay

Git Sync Relay acts as a git repo relay between an upstream git server and the airflow deployment namespace. It uses the [kubernetes/git-sync](https://github.com/kubernetes/git-sync) sidecar to fetch a repo, and an additional container to expose this repo to the local namespace. This has been tested to work when logging into the git remote with authenticated git+ssh, and unauthenticated https.

<img src="./git-sync-relay.svg">

## Manual installation and management

When using this chart outside of Astronomer, for instance when testing or developing, if you are authenticating the git-sync-relay using ssh, you must manage a kubernetes secret that contains the ssh key. This is not managed by helm so that it is never stored in plaintext in the Astronomer houston database. Using k8s secrets for any fields that can contain credentials, such as environment variables, is standard practice in Astronomer components. This is also how it is implemented in the OSS helm chart <https://github.com/apache/airflow/blob/c8e6e5d52f999e9f/chart/values.yaml#L1493-L1511>

### Create an ssh key pair with no passphrase

First, create an ssh key that has no passphrase:

```sh
ssh-keygen -P '' -t ed25519 -f ssh-sync-key-id -C "test key $USER@$HOSTNAME $(date +%FT%T%z)"
```

### Create a k8s secret from the private key

We create a k8s generic secret where the key is stored under `data.gitSshKey`, which is the required location for the private key:

```sh
kubectl create secret generic my-secret --from-file=gitSshKey=ssh-sync-key-id
```

### Add the pub key to your repo

Take the `ssh-sync-key-id.pub` contents and add it to your https://github.com/settings/keys or whatever server you're cloning from.

### Install airflow-chart

Create a `values.yaml` file with contents similar to the following:

```yaml
gitSyncRelay:
  enabled: True
  repo:
    url: https://github.com/astronomer/airflow-example-dags
    branch: main
    depth: 1 # default to a shallow clone because it is faster, though it sacrifices git history
    wait: 60 # seconds between synchronizations with upstream git repo
    subPath: dags # if your dags dir is not the repo root, specify the path relative to the repo root
    sshPrivateKeySecretName: theGitSshPrivateKeyName # The name of a secret that holds the private key.
```

### Install airflow

Then install airflow like you normally would. Assuming your cwd is the root dir or the astronomer/airflow-chart repo:

```sh
helm install airflow . -n aftest -f values.yaml
```
