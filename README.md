# Astronomer's Helm Chart for Apache Airflow

This chart will bootstrap an [Airflow](https://github.com/astronomer/ap-airflow) deployment on a [Kubernetes](http://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

## Quickstart

To install this helm chart remotely (using helm 3)

```bash
kubectl create namespace airflow

helm repo add astronomer https://helm.astronomer.io
helm install airflow --namespace airflow astronomer/airflow
```

To install airflow with the KEDA autoscaler

```bash
helm repo add kedacore https://kedacore.github.io/charts
helm repo add astronomer https://helm.astronomer.io

helm repo update

kubectl create namespace keda
helm install keda \
    --namespace keda kedacore/keda \
    --version "v1.5.0"

kubectl create namespace airflow

helm install airflow \
    --set executor=CeleryExecutor \
    --set workers.keda.enabled=true \
    --set workers.persistence.enabled=false \
    --namespace airflow \
    astronomer/airflow

```
To install this repository from source
```bash
kubectl create namespace airflow
helm install --namespace airflow .
```

## Prerequisites

- Kubernetes 1.12+
- Helm 2.11+ or Helm 3.0+
- PV provisioner support in the underlying infrastructure

## Installing the Chart
To install the chart with the release name `my-release`:

```bash
helm install --name my-release .
```

The command deploys Airflow on the Kubernetes cluster in the default configuration. The [Parameters](#parameters) section lists the parameters that can be configured during installation.

> **Tip**: List all releases using `helm list`

## Upgrading the Chart

First, look at the [updating documentation](UPDATING.md) to identify any backwards-incompatible changes.

To upgrade the chart with the release name `my-release`:

```bash
helm upgrade --name my-release .
```

## Uninstalling the Chart

To uninstall/delete the `my-release` deployment:

```bash
helm delete my-release
```

The command removes all the Kubernetes components associated with the chart and deletes the release.

## Updating DAGs

### Bake DAGs in Docker image

The recommended way to update your DAGs with this chart is to build a new docker image with the
latest code (`docker build -t my-company/airflow:8a0da78 .`), push it to an accessible
registry (`docker push my-company/airflow:8a0da78`), then update the Airflow pods with that image:

```bash
helm upgrade my-release . \
  --set images.airflow.repository=my-company/airflow \
  --set images.airflow.tag=8a0da78
```

### Deploying DAGs using `git-sync`

`extraContainers`, `extraInitContainers`, `extraVolumes`, and `extraVolumeMounts` can be combined to deploy git-sync. The following example relies on `emptyDir` volumes and works with `KubernetesExecutor`.

```yaml
env:
  - name: AIRFLOW__CORE__DAGS_FOLDER
    value: /usr/local/airflow/dags/latest/airflow/example_dags
scheduler:
  extraInitContainers:
    - name: init-gitsync
      image: k8s.gcr.io/git-sync/git-sync:v3.2.2
      imagePullPolicy: IfNotPresent
      env:
        - name: GIT_SYNC_REPO
          value: https://github.com/apache/airflow.git
        - name: GIT_SYNC_ROOT
          value: /usr/local/airflow/dags
        - name: GIT_SYNC_DEST
          value: latest
        - name: GIT_SYNC_ONE_TIME
          value: "true"
      volumeMounts:
        - mountPath: /usr/local/airflow/dags
          name: dags
          readOnly: false
  extraContainers:
    - name: gitsync
      image: k8s.gcr.io/git-sync/git-sync:v3.2.2
      imagePullPolicy: IfNotPresent
      env:
        - name: GIT_SYNC_REPO
          value: https://github.com/apache/airflow.git
        - name: GIT_SYNC_ROOT
          value: /usr/local/airflow/dags
        - name: GIT_SYNC_DEST
          value: latest
        - name: GIT_SYNC_WAIT
          value: "10"
      volumeMounts:
        - mountPath: /usr/local/airflow/dags
          name: dags
          readOnly: false
  extraVolumeMounts:
    - name: dags
      mountPath: /usr/local/airflow/dags
  extraVolumes:
    - name: dags
      emptyDir: {}
workers:
  extraInitContainers:
    - name: gitsync
      image: k8s.gcr.io/git-sync/git-sync:v3.2.2
      imagePullPolicy: IfNotPresent
      env:
        - name: GIT_SYNC_REPO
          value: https://github.com/apache/airflow.git
        - name: GIT_SYNC_ROOT
          value: /usr/local/airflow/dags
        - name: GIT_SYNC_DEST
          value: latest
        - name: GIT_SYNC_ONE_TIME
          value: "true"
      volumeMounts:
        - mountPath: /usr/local/airflow/dags
          name: dags
          readOnly: false
  extraVolumeMounts:
    - name: dags
      mountPath: /usr/local/airflow/dags
  extraVolumes:
    - name: dags
      emptyDir: {}
```

## Docker Images

* The Airflow image that are referenced as the default values in this chart are generated from this repository: https://github.com/astronomer/ap-airflow.
* Other non-airflow images used in this chart are generated from this repository: https://github.com/astronomer/ap-vendor.

## Parameters

The complete list of parameters supported by the community chart can be found on the [Parameteres Reference](https://airflow.apache.org/docs/helm-chart/stable/parameters-ref.html) page, and can be set under the `airflow` key in this chart.


The following tables lists the configurable parameters of the Astronomer chart and their default values.

| Parameter                                             | Description                                                                                               | Default                                                           |    |
|:------------------------------------------------------|:----------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------|:---|
| `ingress.enabled`                                     | Enable Kubernetes Ingress support                                                                         | `false`                                                           |    |
| `ingress.acme`                                        | Add acme annotations to Ingress object                                                                    | `false`                                                           |    |
| `ingress.tlsSecretName`                               | Name of secret that contains a TLS secret                                                                 | `~`                                                               |    |
| `ingress.webserverAnnotations`                        | Annotations added to Webserver Ingress object                                                             | `{}`                                                              |    |
| `ingress.flowerAnnotations`                           | Annotations added to Flower Ingress object                                                                | `{}`                                                              |    |
| `ingress.baseDomain`                                  | Base domain for VHOSTs                                                                                    | `~`                                                               |    |
| `ingress.auth.enabled`                                | Enable auth with Astronomer Platform                                                                      | `true`                                                            |    |
| `workers.autoscaling.enabled`                         | Traditional HorizontalPodAutoscaler                                                                       | `false`                                                           |    |
| `workers.autoscaling.minReplicas`                     | Minimum amount of workers                                                                                 | `1`                                                               |    |
| `workers.autoscaling.maxReplicas`                     | Maximum amount of workers                                                                                 | `10`                                                              |    |
| `workers.autoscaling.targetCPUUtilization`            | Target CPU Utilization of workers                                                                         | `80`                                                              |    |
| `workers.autoscaling.targetMemoryUtilization`         | Target Memory Utilization of workers                                                                      | `80`                                                              |    |
| `extraObjects`                                        | Extra K8s Objects to deploy (these are passed through `tpl`). More about [Extra Objects](#extra-objects). | `[]`                                                              |    |
| `sccEnabled`                                          | Enable security context constraints required for OpenShift                                                | `false`                                                           |    |


Specify each parameter using the `--set key=value[,key=value]` argument to `helm install`. For example,

```bash
helm install --name my-release \
  --set executor=CeleryExecutor \
  --set enablePodLaunching=false .
```

##  Autoscaling with KEDA

KEDA stands for Kubernetes Event Driven Autoscaling. [KEDA](https://github.com/kedacore/keda) is a custom controller that allows users to create custom bindings
to the Kubernetes [Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/).
We've built an experimental scaler that allows users to create scalers based on postgreSQL queries. For the moment this exists
on a separate branch, but will be merged upstream soon. To install our custom version of KEDA on your cluster, please run

```bash
helm repo add kedacore https://kedacore.github.io/charts

helm repo update

helm install \
    --set image.keda=docker.io/kedacore/keda:1.2.0 \
    --set image.metricsAdapter=docker.io/kedacore/keda-metrics-adapter:1.2.0 \
    --namespace keda --name keda kedacore/keda
```

Once KEDA is installed (which should be pretty quick since there is only one pod). You can try out KEDA autoscaling
on this chart by setting `workers.keda.enabled=true` your helm command or in the `values.yaml`.
(Note: KEDA does not support StatefulSets so you need to set `worker.persistence.enabled` to `false`)

```bash
helm repo add astronomer https://helm.astronomer.io
helm repo update

kubectl create namespace airflow

helm install airflow \
    --set executor=CeleryExecutor \
    --set workers.keda.enabled=true \
    --set workers.persistence.enabled=false \
    --namespace airflow \
    astronomer/airflow
```

## Walkthrough using kind

**Install kind, and create a cluster:**

We recommend testing with Kubernetes 1.16+, example:

```
kind create cluster \
  --image kindest/node:v1.18.15
```

Confirm it's up:

```
kubectl cluster-info --context kind-kind
```

**Add Astronomer's Helm repo:**

```
helm repo add astronomer https://helm.astronomer.io
helm repo update
```

**Create namespace + install the chart:**

```
kubectl create namespace airflow
helm install airflow -n airflow astronomer/airflow
```

It may take a few minutes. Confirm the pods are up:

```
kubectl get pods --all-namespaces
helm list -n airflow
```

Run `kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow`
to port-forward the Airflow UI to http://localhost:8080/ to confirm Airflow is working.

**Build a Docker image from your DAGs:**

1. Start a project using [astro-cli](https://github.com/astronomer/astro-cli), which will generate a Dockerfile, and load your DAGs in. You can test locally before pushing to kind with `astro airflow start`.

        mkdir my-airflow-project && cd my-airflow-project
        astro dev init

2. Then build the image:

        docker build -t my-dags:0.0.1 .

3. Load the image into kind:

        kind load docker-image my-dags:0.0.1

4. Upgrade Helm deployment:

        helm upgrade airflow -n airflow \
            --set images.airflow.repository=my-dags \
            --set images.airflow.tag=0.0.1 \
            astronomer/airflow

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
