# Astronomer's Helm Chart for Apache Airflow 

[Apache Airflow](https://airflow.apache.org/) is a platform to programmatically author, schedule and monitor workflows. [Astronomer](https://www.astronomer.io/) is a software company built around Airflow. We have extracted this Helm Chart from our platform Helm chart and made it accessible under Apache 2 license.

## TL;DR

```console
helm install .
```

## Introduction

This chart will bootstrap an [Airfow](https://github.com/astronomer/astronomer/tree/master/docker/airflow) deployment on a [Kubernetes](http://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

## Prerequisites

- Kubernetes 1.12+
- Helm 2.11+ or Helm 3.0-beta3+
- PV provisioner support in the underlying infrastructure

## Installing the Chart
To install the chart with the release name `my-release`:

```console
helm install --name my-release .
```

The command deploys Airflow on the Kubernetes cluster in the default configuration. The [Parameters](#parameters) section lists the parameters that can be configured during installation.

> **Tip**: List all releases using `helm list`

## Upgrading the Chart
To upgrade the chart with the release name `my-release`:

```console
helm upgrade --name my-release .
```

## Uninstalling the Chart

To uninstall/delete the `my-release` deployment:

```console
helm delete my-release
```

The command removes all the Kubernetes components associated with the chart and deletes the release.

## Updating DAGs

The recommended way to update your DAGs with this chart is to build a new docker image with the latest code (`docker build -t my-company/airflow:8a0da78 .`), push it to an accessible registry (`docker push my-company/airflow:8a0da78`), then update the Airflow pods with that image:

```console
helm upgrade my-release . \
  --set images.airflow.repository=my-company/airflow \
  --set images.airflow.tag=8a0da78
```

## Parameters

The following tables lists the configurable parameters of the Airflow chart and their default values.

| Parameter                           | Description                                                                                                  | Default                                           |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------- |
| `uid`                               | UID to run airflow pods under                                                                                | `nil`                                             |
| `gid`                               | GID to run airflow pods under                                                                                | `nil`                                             |
| `nodeSelector`                      | Node labels for pod assignment                                                                               | `{}`                                              |
| `affinity`                          | Affinity labels for pod assignment                                                                           | `{}`                                              |
| `tolerations`                       | Toleration labels for pod assignment                                                                         | `[]`                                              |
| `labels`                            | Common labels to add to all objects defined in this chart                                                    | `{}`                                              |
| `privateRegistry.enabled`           | Enable usage of a private registry for Airflow base image                                                    | `false`                                           |
| `privateRegistry.repository`        | Repository where base image lives (eg: quay.io)                                                              | `~`                                               |
| `ingress.enabled`                   | Enable Kubernetes Ingress support                                                                            | `false`                                           |
| `ingress.acme`                      | Add acme annotations to Ingress object                                                                       | `false`                                           |
| `ingress.tlsSecretName`             | Name of secret that contains a TLS secret                                                                    | `~`                                               |
| `ingress.baseDomain`                | Base domain for VHOSTs                                                                                       | `~`                                               |
| `ingress.class`                     | Ingress class to associate with                                                                              | `nginx`                                           |
| `ingress.auth.enabled`              | Enable auth with Astronomer Platform                                                                         | `true`                                            |
| `networkPolicies.enabled`           | Enable Network Policies to restrict traffic                                                                  | `true`                                            |
| `airflowHome`                       | Location of airflow home directory                                                                           | `/usr/local/airflow`                              |
| `rbacEnabled`                       | Deploy pods with Kubernets RBAC enabled                                                                      | `true`                                            |
| `airflowVersion`                    | Default Airflow image version                                                                                | `1.10.5`                                          |
| `executor`                          | Airflow executor (eg SequentialExecutor, LocalExecutor, CeleryExecutor, KubernetesExecutor)                  | `KubernetesExecutor`                              |
| `allowPodLaunching`                 | Allow airflow pods to talk to Kubernetes API to launch more pods                                             | `true`                                            |


Specify each parameter using the `--set key=value[,key=value]` argument to `helm install`. For example,

```console
helm install --name my-release \
  --set executor=CeleryExecutor \
  --set enablePodLaunching=false .
```

## Contributing

Check out [our contributing guide!](CONTRIBUTING.md)

##  Autoscaling with KEDA

KEDA stands for Kubernetes Event Driven Autoscaling. KEDA is a custom controller that allows users to create custom bindings
to the Kubernetes [Horizontal Pod Autoscaler](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/).
We've built an experimental scaler that allows users to create scalers based on postgreSQL queries. For the moment this exists
on a seperate branch, but will be merged upstream soon. To install our custom version of KEDA on your cluster, please run

```console
helm repo add kedacore https://kedacore.github.io/charts

helm repo update

helm install \
    --set image.keda=dimberman/keda:master \
    --set image.metricsAdapter=dimberman/keda-metrics-adapter:master \
    --namespace keda --name keda kedacore/keda
```

Once KEDA is installed (which should be pretty quick since there is only one pod). You can try out KEDA autoscaling 
on this chart by setting `workers.keda.enabled=true` your helm command or in the `values.yaml`. 
(Note: KEDA does not support StatefulSets so you need to set `worker.persistence.enabled` to `false`)

```console
helm install \
    --name airflow \
    --set executor=CeleryExecutor \
    --set workers.keda.enabled=true \
    --set workers.persistence.enabled=false \
    --namespace airflow \
    -f values.yaml .
```