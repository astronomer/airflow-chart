# Contributing

## Local development

You can run Kubernetes in Docker (kind) in order to develop this chart on your workstation.

### Install dependencies

- Docker

Make sure your user has access to Docker:
```
docker run --rm hello-world:latest
```

### Deploy the chart locally

To delete an existing kind cluster and reinstall the helm chart from scratch

```
# Optionally, you can specify a kubernetes version
KUBE_VERSION=1.15.6

bin/reset-local-dev
```

The above script takes the following steps:
- Install dependencies: kind, kubectl, helm
- Delete existing kind cluster named 'kind', if it exists
- Start a new kind cluster
- Install Tiller in the kind cluster
- Deploy Airflow in the kind cluster

## Testing

See [tests/README.md](tests/README.md) for instruction on how to write tests for chart changes.
