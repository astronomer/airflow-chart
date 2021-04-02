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

The recommended way to update your DAGs with this chart is to build a new docker image with the latest code (`docker build -t my-company/airflow:8a0da78 .`), push it to an accessible registry (`docker push my-company/airflow:8a0da78`), then update the Airflow pods with that image:

```bash
helm upgrade my-release . \
  --set images.airflow.repository=my-company/airflow \
  --set images.airflow.tag=8a0da78
```

## Docker Images

* The Airflow image that are referenced as the default values in this chart are generated from this repository: https://github.com/astronomer/ap-airflow.
* Other non-airflow images used in this chart are generated from this repository: https://github.com/astronomer/ap-vendor.

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| affinity | object | `{}` | Kubernetes affinity |
| airflowHome | string | `"/usr/local/airflow"` | Airflow home directory, used for mount paths. |
| airflowPodAnnotations | object | `{}` | Extra annotations to apply to all airflow pods |
| airflowVersion | string | `"2.0.0"` | Airflow version |
| allowPodLaunching | bool | `true` |  |
| cleanup.enabled | bool | `false` |  |
| cleanup.schedule | string | `"*/15 * * * *"` |  |
| createUserJobAnnotations | object | `{}` | Extra annotations to apply to Create user job |
| data.metadataConnection.db | string | `"postgres"` |  |
| data.metadataConnection.host | string | `nil` |  |
| data.metadataConnection.pass | string | `"postgres"` |  |
| data.metadataConnection.port | int | `5432` |  |
| data.metadataConnection.sslmode | string | `"disable"` |  |
| data.metadataConnection.user | string | `"postgres"` |  |
| data.metadataSecretName | string | `nil` | If provided, use this secrets |
| data.resultBackendConnection.db | string | `"postgres"` |  |
| data.resultBackendConnection.host | string | `nil` |  |
| data.resultBackendConnection.pass | string | `"postgres"` |  |
| data.resultBackendConnection.port | int | `5432` |  |
| data.resultBackendConnection.sslmode | string | `"disable"` |  |
| data.resultBackendConnection.user | string | `"postgres"` |  |
| data.resultBackendSecretName | string | `nil` | If provided, use this secrets |
| defaultAirflowRepository | string | `"quay.io/astronomer/ap-airflow"` | Default repository in which to look for airflow images |
| defaultAirflowTag | string | `"2.0.0-buster"` | Default airflow tag to deploy |
| elasticsearch.connection.scheme | string | `"http"` |  |
| elasticsearch.enabled | bool | `false` |  |
| elasticsearch.secretName | string | `nil` |  |
| env | list | `[]` | Environment variables for all airflow containers other than init containers. |
| executor | string | `"KubernetesExecutor"` |  |
| extraObjects | list | `[]` |  |
| fernetKey | string | `nil` |  |
| fernetKeySecretName | string | `nil` |  |
| flower.resources | object | `{}` |  |
| gid | int | `50000` | Group of airflow user |
| images.airflow.pullPolicy | string | `"IfNotPresent"` |  |
| images.airflow.repository | string | `"quay.io/astronomer/ap-airflow"` |  |
| images.airflow.tag | string | `nil` |  |
| images.pgbouncer.pullPolicy | string | `"IfNotPresent"` |  |
| images.pgbouncer.repository | string | `"quay.io/astronomer/ap-pgbouncer"` |  |
| images.pgbouncer.tag | string | `"0.11.0"` |  |
| images.pgbouncerExporter.pullPolicy | string | `"IfNotPresent"` |  |
| images.pgbouncerExporter.repository | string | `"quay.io/astronomer/ap-pgbouncer-exporter"` |  |
| images.pgbouncerExporter.tag | string | `"0.11.0"` |  |
| images.redis.pullPolicy | string | `"IfNotPresent"` |  |
| images.redis.repository | string | `"quay.io/astronomer/ap-redis"` |  |
| images.redis.tag | string | `"0.11.0"` |  |
| images.statsd.pullPolicy | string | `"IfNotPresent"` |  |
| images.statsd.repository | string | `"quay.io/astronomer/ap-statsd-exporter"` |  |
| images.statsd.tag | string | `"0.18.0"` |  |
| ingress.acme | bool | `false` | Enable for cert-manager or kube-lego |
| ingress.auth | object | `{"enabled":true}` | Enable platform authentication |
| ingress.baseDomain | string | `nil` | Base domain for ingress vhosts |
| ingress.enabled | bool | `false` | Enable ingress resource |
| ingress.flowerAnnotations | object | `{}` | Annotations always injected when configuring Flower Ingress object |
| ingress.tlsSecretName | string | `nil` | Name of tls secret to use on ingress |
| ingress.webserverAnnotations | object | `{}` | Annotations always injected when configuring webserver Ingress object |
| labels | object | `{}` | Add common labels to all objects and pods defined in this chart. |
| limits | list | `[]` |  |
| mountAllFromSecretName | string | `nil` | Pass a secret name here to mount all keys as environment variables in the Airflow pods. |
| networkPolicies.enabled | bool | `false` | Enabled network policies |
| nodeSelector | object | `{}` | Select certain nodes for airflow pods. |
| pgbouncer.enabled | bool | `false` |  |
| pgbouncer.extraIniDatabaseMetatdata | string | `""` |  |
| pgbouncer.extraIniDatabaseResultBackend | string | `""` |  |
| pgbouncer.extraIniPgbouncerConfig | string | `""` |  |
| pgbouncer.extraNetworkPolicies | list | `[]` |  |
| pgbouncer.logConnections | int | `0` |  |
| pgbouncer.logDisconnections | int | `0` |  |
| pgbouncer.maxClientConn | int | `100` |  |
| pgbouncer.metadataPoolSize | int | `3` |  |
| pgbouncer.podDisruptionBudget.config.maxUnavailable | int | `1` |  |
| pgbouncer.podDisruptionBudget.enabled | bool | `false` |  |
| pgbouncer.resources | object | `{}` |  |
| pgbouncer.resultBackendPoolSize | int | `2` |  |
| pgbouncer.serverTlsSslmode | string | `"prefer"` |  |
| pgbouncer.verbose | int | `0` |  |
| platform.release | string | `nil` |  |
| platform.workspace | string | `""` |  |
| podMutation.affinity | object | `{}` |  |
| podMutation.tolerations | list | `[]` |  |
| ports.airflowUI | int | `8080` |  |
| ports.flowerUI | int | `5555` |  |
| ports.pgbouncer | int | `6543` |  |
| ports.pgbouncerScrape | int | `9127` |  |
| ports.redisDB | int | `6379` |  |
| ports.statsdIngest | int | `9125` |  |
| ports.statsdScrape | int | `9102` |  |
| ports.workerLogs | int | `8793` |  |
| postgresql.enabled | bool | `true` |  |
| postgresql.postgresqlPassword | string | `"postgres"` |  |
| postgresql.postgresqlUsername | string | `"postgres"` |  |
| quotas | object | `{}` |  |
| rbacEnabled | bool | `true` | Enable RBAC (default on most clusters these days) |
| redis.brokerURLSecretName | string | `nil` |  |
| redis.password | string | `nil` |  |
| redis.passwordSecretName | string | `nil` |  |
| redis.persistence.enabled | bool | `true` |  |
| redis.persistence.size | string | `"1Gi"` |  |
| redis.persistence.storageClassName | string | `nil` |  |
| redis.resources | object | `{}` |  |
| redis.safeToEvict | bool | `true` |  |
| redis.terminationGracePeriodSeconds | int | `600` |  |
| registry.connection | object | `{}` |  |
| registry.secretName | string | `nil` |  |
| runMigrationsJobAnnotations | object | `{}` | Extra annotations to apply to run migrations job |
| sccEnabled | bool | `false` |  |
| scheduler.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[0].podAffinityTerm.labelSelector.matchExpressions[0].key | string | `"component"` |  |
| scheduler.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[0].podAffinityTerm.labelSelector.matchExpressions[0].operator | string | `"In"` |  |
| scheduler.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[0].podAffinityTerm.labelSelector.matchExpressions[0].values[0] | string | `"scheduler"` |  |
| scheduler.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[0].podAffinityTerm.topologyKey | string | `"kubernetes.io/hostname"` |  |
| scheduler.affinity.podAntiAffinity.preferredDuringSchedulingIgnoredDuringExecution[0].weight | int | `100` |  |
| scheduler.airflowLocalSettings | string | `nil` |  |
| scheduler.extraContainers | list | `[]` |  |
| scheduler.extraVolumeMounts | list | `[]` |  |
| scheduler.extraVolumes | list | `[]` |  |
| scheduler.livenessProbe.failureThreshold | int | `10` |  |
| scheduler.livenessProbe.initialDelaySeconds | int | `10` |  |
| scheduler.livenessProbe.periodSeconds | int | `30` |  |
| scheduler.livenessProbe.timeoutSeconds | int | `30` |  |
| scheduler.replicas | int | `1` |  |
| scheduler.resources | object | `{}` |  |
| scheduler.safeToEvict | bool | `true` |  |
| secret | list | `[]` | Secrets for all airflow containers other than init containers. |
| serviceAccountAnnotations | object | `{}` | Extra annotations to apply to service accounts |
| statsd.enabled | bool | `true` |  |
| statsd.resources | object | `{}` |  |
| tolerations | list | `[]` | Kubernetes tolerations |
| uid | int | `50000` | User of airflow user |
| webserver.allowPodLogReading | bool | `false` |  |
| webserver.defaultUser.email | string | `"admin@example.com"` |  |
| webserver.defaultUser.enabled | bool | `true` |  |
| webserver.defaultUser.firstName | string | `"admin"` |  |
| webserver.defaultUser.lastName | string | `"user"` |  |
| webserver.defaultUser.password | string | `"admin"` |  |
| webserver.defaultUser.role | string | `"Admin"` |  |
| webserver.defaultUser.username | string | `"admin"` |  |
| webserver.extraContainers | list | `[]` |  |
| webserver.jwtSigningCertificateSecretName | string | `nil` |  |
| webserver.livenessProbe.failureThreshold | int | `20` |  |
| webserver.livenessProbe.initialDelaySeconds | int | `15` |  |
| webserver.livenessProbe.periodSeconds | int | `5` |  |
| webserver.livenessProbe.timeoutSeconds | int | `30` |  |
| webserver.readinessProbe.failureThreshold | int | `20` |  |
| webserver.readinessProbe.initialDelaySeconds | int | `15` |  |
| webserver.readinessProbe.periodSeconds | int | `5` |  |
| webserver.readinessProbe.timeoutSeconds | int | `30` |  |
| webserver.replicas | int | `1` |  |
| webserver.resources | object | `{}` |  |
| workers.additionalVolume.accessMode | string | `nil` |  |
| workers.additionalVolume.capacity | string | `nil` |  |
| workers.additionalVolume.enabled | bool | `false` |  |
| workers.additionalVolume.mountPath | string | `nil` |  |
| workers.additionalVolume.storageClassName | string | `nil` |  |
| workers.additionalVolume.volumeMode | string | `nil` |  |
| workers.additionalVolume.volumePlugin | object | `{}` |  |
| workers.autoscaling.enabled | bool | `false` |  |
| workers.autoscaling.maxReplicas | int | `10` |  |
| workers.autoscaling.minReplicas | int | `1` |  |
| workers.autoscaling.targetCPUUtilization | int | `80` |  |
| workers.autoscaling.targetMemoryUtilization | int | `80` |  |
| workers.extraContainers | list | `[]` |  |
| workers.extraVolumeMounts | list | `[]` |  |
| workers.extraVolumes | list | `[]` |  |
| workers.keda.cooldownPeriod | int | `30` |  |
| workers.keda.enabled | bool | `false` |  |
| workers.keda.namespaceLabels | object | `{}` |  |
| workers.keda.pollingInterval | int | `5` |  |
| workers.persistence.enabled | bool | `false` |  |
| workers.persistence.fixPermissions | bool | `false` |  |
| workers.persistence.size | string | `"100Gi"` |  |
| workers.persistence.storageClassName | string | `nil` |  |
| workers.replicas | int | `1` |  |
| workers.resources | object | `{}` |  |
| workers.safeToEvict | bool | `true` |  |
| workers.strategy.rollingUpdate.maxSurge | string | `"100%"` |  |
| workers.strategy.rollingUpdate.maxUnavailable | string | `"50%"` |  |
| workers.terminationGracePeriodSeconds | int | `600` |  |
| workers.updateStrategy | string | `nil` |  |

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

We recommend testing with Kubernetes 1.15, as this image doesn't support Kubernetes 1.16+ for CeleryExecutor presently.

```
kind create cluster \
  --image kindest/node:v1.15.7@sha256:e2df133f80ef633c53c0200114fce2ed5e1f6947477dbc83261a6a921169488d
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
