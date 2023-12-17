# Contributing

## Local development

You can run Kubernetes in Docker (kind) in order to develop this chart on your workstation.

### Install dependencies

- Docker

Make sure your user has access to Docker:

```sh
docker run --rm hello-world:latest
```

### Deploy the chart locally

To delete an existing kind cluster and reinstall the helm chart from scratch

```sh
# Optionally, you can specify a kubernetes version available from https://hub.docker.com/r/kindest/node/tags
KUBE_VERSION=1.24.13

bin/reset-local-dev
```

The above script takes the following steps:

- Install dependencies: kind, kubectl, helm
- Delete existing kind cluster named 'kind', if it exists
- Start a new kind cluster
- Install Tiller in the kind cluster
- Deploy Airflow in the kind cluster

### Accessing services deployed by the chart

The easiest way to access services after the chart has been installed is to use the [`kubefwd`](https://github.com/txn2/kubefwd) tool. `bin/reset-local-dev` installs the chart into the `airflow` namespace. Run the following command to expose all of the services within that namespace so they are accessible by dns names:

```sh
sudo -E kubefwd svc -n airflow
```

The output will look something like:

```
INFO[11:55:18]  _          _           __             _
INFO[11:55:18] | | ___   _| |__   ___ / _|_      ____| |
INFO[11:55:18] | |/ / | | | '_ \ / _ \ |_\ \ /\ / / _  |
INFO[11:55:18] |   <| |_| | |_) |  __/  _|\ V  V / (_| |
INFO[11:55:18] |_|\_\\__,_|_.__/ \___|_|   \_/\_/ \__,_|
INFO[11:55:18]
INFO[11:55:18] Version 1.22.5
INFO[11:55:18] https://github.com/txn2/kubefwd
INFO[11:55:18]
INFO[11:55:18] Press [Ctrl-C] to stop forwarding.
INFO[11:55:18] 'cat /etc/hosts' to see all host entries.
INFO[11:55:18] Loaded hosts file /etc/hosts
INFO[11:55:18] HostFile management: Original hosts backup already exists at /Users/testuser/hosts.original
INFO[11:55:18] Successfully connected context: kind-kind
WARN[11:55:18] WARNING: Skipped Port-Forward for chart-1702669617-statsd:9125 to pod chart-1702669617-statsd-79d84847b4-xtj6l:9125 - k8s port-forwarding doesn't support UDP protocol
INFO[11:55:18] Port-Forward:       127.1.27.1 chart-1702669617-statsd:9102 to pod chart-1702669617-statsd-79d84847b4-xtj6l:9102
INFO[11:55:18] Port-Forward:       127.1.27.2 chart-1702669617-webserver:8080 to pod chart-1702669617-webserver-5749fc855c-x649p:8080
INFO[11:55:18] Port-Forward:       127.1.27.3 chart-1702669617-postgresql-hl:5432 to pod chart-1702669617-postgresql-0:5432
INFO[11:55:18] Port-Forward:       127.1.27.4 chart-1702669617-postgresql-0.chart-1702669617-postgresql-hl:5432 to pod chart-1702669617-postgresql-0:5432
INFO[11:55:18] Port-Forward:       127.1.27.5 chart-1702669617-postgresql:5432 to pod chart-1702669617-postgresql-0:5432
```

You should then be able to access each service at its domain name and port pair as shown.

## Testing

See [tests/README.md](tests/README.md) for instruction on how to write tests for chart changes.
