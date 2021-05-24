# Updating Astronomer's Helm Chart for Apache Airflow

This file documents any backwards-incompatible changes in the Astronomer Airflow Helm chart and
assists users migrating to a new version.

## 1.0.0

`1.0.0` takes a new approach by building on top of the official community Helm chart. This changes requires some renaming and adjusting in your values, documented below.

### Parameter Root

As we now build on top of the official community Helm chart, most of the parameters have been moved under the `airflow` key.
For example, to set `airflowVersion`, `defaultAirflowTag`, and `executor`:

```yaml
 airflow:
   airflowVersion: 2.1.0
   defaultAirflowTag: 2.1.0-1-buster
   executor: CeleryExecutor
```

The complete list of parameters supported by the community chart can be found on the [Parameteres Reference](https://airflow.apache.org/docs/helm-chart/stable/parameters-ref.html) page.

### Renamed Parameters

| From                                      | To                                                |
| ----------------------------------------- | ------------------------------------------------- |
| `createUserJobAnnotations`                | `airflow.createUserJob.annotations`               |
| `runMigrationsJobAnnotations`             | `airflow.migrateDatabaseJob.annotations`          |
| `rbacEnabled`                             | `airflow.rbac.create`                             |
| `scheduler.airflowLocalSettings`          | `airflow.airflowLocalSettings`                    |
| `pgbouncer.extraIniDatabaseMetatdata` (yes, typo is correct) | `airflow.pgbouncer.extaIniMetadata` |
| `pgbouncer.extraIniDatabaseResultBackend` | `airflow.pgbouncer.extaIniResultBackend`          |
| `pgbouncer.extraIniPgbouncerConfig`       | `airflow.pgbouncer.extaIni`                       |

### ServiceAccount Annotations

ServiceAcccounts, and the annotations that are applied to them, are now separated for each component of Airflow.

For example, previously you would do:

```yaml
airflow:
  serviceAccountAnnotations:
    some-annotation: hello
```

Now you would do the following to apply the annotation to the scheduler ServiceAccount:

```yaml
airflow:
  scheduler:
    serviceAccount:
      annotations:
        some-annotation: hello
```

### Environment Variables from a Secret

Instead of using `mountAllFromSecretName`, you now use `extraEnvFrom`:

```yaml
airflow:
  extraEnvFrom: |-
    - secretRef:
      name: 'some-secret'
```

### Additional Volume for Workers

Instead of using `workers.additionalVolume`, you now use `workers.extraVolumes`, `workers.extraVolumeMounts`, and `extraObjects`:

```yaml
airflow:
  workers:
      extraVolumes:
         - name: worker-volume
           persistentVolumeClaim:
             claimName: worker-claim
      extraVolumeMounts:
        - name: worker-volume
          mountPath: /some-mount-path
extraObjects:
  - apiVersion: v1
    kind: PersistentVolume
    metadata:
      name: {{ .Release.Name }}-worker-pv
      labels:
        tier: airflow
        component: worker
        release: {{ .Release.Name }}
        chart: "{{ .Chart.Name }}-{{ .Chart.Version }}"
        heritage: {{ .Release.Service }}
    {{- with .Values.airflow.labels }}
    {{ toYaml . | indent 4 }}
    {{- end }}
    spec:
      capacity:
        storage: 5Gi
      volumeMode: Filesystem
      accessModes:
        - ReadWriteMany
      persistentVolumeReclaimPolicy: Delete
  - apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      name: {{ .Release.Name }}-worker-claim
      labels:
        tier: airflow
        component: worker
        release: {{ .Release.Name }}
        chart: "{{ .Chart.Name }}-{{ .Chart.Version }}"
        heritage: {{ .Release.Service }}
    {{- with .Values.airflow.labels }}
    {{ toYaml . | indent 4 }}
    {{- end }}
    spec:
      accessModes:
        - ReadWriteMany
      resources:
        requests:
          storage: 5Gi
```
