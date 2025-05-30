# Astronomer's Helm Chart for Apache Airflow

This chart will bootstrap an [Airflow](https://github.com/astronomer/ap-airflow) deployment on a [Kubernetes](http://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

The version of this chart does not correlate to any other component. If it happens to align with OSS airflow that is just a coincidence. Users should not expect feature parity between OSS airflow chart and the Astronomer airflow-chart for identical version numbers.

## Quickstart

To install this helm chart remotely (using helm 3)

```sh
kubectl create namespace airflow

helm repo add astronomer https://helm.astronomer.io
helm install airflow --namespace airflow astronomer/airflow
```

To install this repository from source

```sh
kubectl create namespace airflow
helm install --namespace airflow .
```

## Prerequisites

- Kubernetes 1.12+
- Helm 3.6+
- PV provisioner support in the underlying infrastructure

## Installing the Chart

To install the chart with the release name `my-release`:

```sh
helm install --name my-release .
```

The command deploys Airflow on the Kubernetes cluster in the default configuration. The [Parameters](#parameters) section lists the parameters that can be configured during installation.

> **Tip**: List all releases using `helm list`

## Upgrading the Chart

First, look at the [updating documentation](UPDATING.md) to identify any backwards-incompatible changes.

To upgrade the chart with the release name `my-release`:

```sh
helm upgrade --name my-release .
```

## Uninstalling the Chart

To uninstall/delete the `my-release` deployment:

```sh
helm delete my-release
```

The command removes all the Kubernetes components associated with the chart and deletes the release.

## Updating DAGs

### Bake DAGs in Docker image

The recommended way to update your DAGs with this chart is to build a new docker image with the
latest code (`docker build -t my-company/airflow:8a0da78 .`), push it to an accessible
registry (`docker push my-company/airflow:8a0da78`), then update the Airflow pods with that image:

```sh
helm upgrade my-release . \
  --set images.airflow.repository=my-company/airflow \
  --set images.airflow.tag=8a0da78
```

## Docker Images

- The Airflow image that are referenced as the default values in this chart are generated from this repository: https://github.com/astronomer/ap-airflow.
- Other non-airflow images used in this chart are generated from this repository: https://github.com/astronomer/ap-vendor.

## Parameters

The complete list of parameters supported by the community chart can be found on the [Parameteres Reference](https://airflow.apache.org/docs/helm-chart/stable/parameters-ref.html) page, and can be set under the `airflow` key in this chart.

The following tables lists the configurable parameters of the Astronomer chart and their default values.

| Parameter                              | Description                                                                                               | Default                       |
| :------------------------------------- | :-------------------------------------------------------------------------------------------------------- | :---------------------------- |
| `ingress.enabled`                      | Enable Kubernetes Ingress support                                                                         | `false`                       |
| `ingress.acme`                         | Add acme annotations to Ingress object                                                                    | `false`                       |
| `ingress.tlsSecretName`                | Name of secret that contains a TLS secret                                                                 | `~`                           |
| `ingress.webserverAnnotations`         | Annotations added to Webserver Ingress object                                                             | `{}`                          |
| `ingress.flowerAnnotations`            | Annotations added to Flower Ingress object                                                                | `{}`                          |
| `ingress.baseDomain`                   | Base domain for VHOSTs                                                                                    | `~`                           |
| `ingress.auth.enabled`                 | Enable auth with Astronomer Platform                                                                      | `true`                        |
| `extraObjects`                         | Extra K8s Objects to deploy (these are passed through `tpl`). More about [Extra Objects](#extra-objects). | `[]`                          |
| `sccEnabled`                           | Enable security context constraints required for OpenShift                                                | `false`                       |
| `authSidecar.enabled`                  | Enable authSidecar                                                                                        | `false`                       |
| `authSidecar.ingressAllowedNamespaces` | List of namespaces from which ingress traffic is allowed to auth sidecar                                  | `[]`                          |
| `authSidecar.repository`               | The image for the auth sidecar proxy                                                                      | `nginxinc/nginx-unprivileged` |
| `authSidecar.tag`                      | The image tag for the auth sidecar proxy                                                                  | `stable`                      |
| `authSidecar.pullPolicy`               | The K8s pullPolicy for the the auth sidecar proxy image                                                   | `IfNotPresent`                |
| `authSidecar.port`                     | The port the auth sidecar exposes                                                                         | `8084`                        |
| `gitSyncRelay.enabled`                 | Enables [git sync relay](docs/git-sync-relay.md) feature.                                                 | `False`                       |
| `gitSyncRelay.repo.url`                | Upstream URL to the git repo to clone.                                                                    | `~`                           |
| `gitSyncRelay.repo.branch`             | Branch of the upstream git repo to checkout.                                                              | `main`                        |
| `gitSyncRelay.repo.depth`              | How many revisions to check out. Leave as default `1` except in dev where history is needed.              | `1`                           |
| `gitSyncRelay.repo.wait`               | Seconds to wait before pulling from the upstream remote.                                                  | `60`                          |
| `gitSyncRelay.repo.subPath`            | Path to the dags directory within the git repository.                                                     | `~`                           |

Specify each parameter using the `--set key=value[,key=value]` argument to `helm install`. For example,

```sh
helm install --name my-release \
  --set executor=CeleryExecutor \
  --set enablePodLaunching=false .
```

## Walkthrough using kind

### Install kind, and create a cluster

We recommend testing with the latest version of kubernetes listed in [metadata.yaml](metadata.yaml):

```sh
kind create cluster --image kindest/node:v1.30.2
```

Confirm it's up:

```sh
kubectl cluster-info --context kind-kind
```

### Add Astronomer's Helm repo

```sh
helm repo add astronomer https://helm.astronomer.io
helm repo update
```

### Create namespace + install the chart

```sh
kubectl create namespace airflow
helm install airflow -n airflow astronomer/airflow
```

It may take a few minutes. Confirm the pods are up:

```sh
kubectl get pods --all-namespaces
helm list -n airflow
```

Run `kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow`
to port-forward the Airflow UI to http://localhost:8080/ to confirm Airflow is working.
Login as _admin_ and password _admin_.

### Build a Docker image from your DAGs

1.  Start a project using [astro-cli](https://github.com/astronomer/astro-cli), which will generate a Dockerfile, and load your DAGs in. You can test locally before pushing to kind with `astro airflow start`.
    ```sh
    mkdir my-airflow-project && cd my-airflow-project
    astro dev init
    ```
2.  Then build the image:
    ```sh
    docker build -t my-dags:0.0.1 .
    ```
3.  Load the image into kind:
    ```sh
    kind load docker-image my-dags:0.0.1
    ```
4.  Upgrade Helm deployment:

    ```sh
    helm upgrade airflow -n airflow \
        --set images.airflow.repository=my-dags \
        --set images.airflow.tag=0.0.1 \
        astronomer/airflow
    ```

## Extra Objects

This chart can deploy extra Kubernetes objects (assuming the role used by Helm can manage them). For Astronomer Cloud and Enterprise, the role permissions can be found in the [Commander role](https://github.com/astronomer/astronomer/blob/master/charts/astronomer/templates/commander/commander-role.yaml).

```yaml
extraObjects:
  - apiVersion: batch/v1beta1
    kind: CronJob
    metadata:
      name: "{{ .Release.Name }}-somejob"
    spec:
      schedule: "*/10 * * * *"
      concurrencyPolicy: Forbid
      jobTemplate:
        spec:
          template:
            spec:
              containers:
                - name: myjob
                  image: ubuntu
                  command:
                    - echo
                  args:
                    - hello
              restartPolicy: OnFailure
```

## Contributing

Check out [our contributing guide!](CONTRIBUTING.md)

## License

Apache 2.0 with Commons Clause
