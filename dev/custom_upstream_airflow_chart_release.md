# Releasing a custom version of the OSS Airflow chart

`airflow-chart` uses the [OSS Airflow chart](https://github.com/apache/airflow/tree/main/chart) as a subchart, which allows for less duplication and more consistency between the charts.

Sometimes, however, we will need to release a version of `airflow-chart` out-of-band with the official community chart, for example to fix a bug.
This can be achieved with the following process, which will assume we need to release a `1.3.1` based on `1.3.0`.

In the [astronomer/airflow](https://github.com/astronomer/airflow) repo:

1. Create and checkout a new branch for the release:

```shell
$ git checkout -b helm-chart/v1-3-1 helm-chart/1.3.0
```

2. Cherry-pick GitHub Actions workflow:

```shell
$ git cherry-pick -x d2f74461
```

> **_NOTE:_** Find the commit with the latest version of the workflow by looking at the last custom release, e.g. in the branch `helm-chart/v1-3-0`.

3. Bump the chart version in `Chart.yaml`

4. Push the branch

```shell
$ git push
```

5. Create and push tag

```shell
$ git tag -s oss-helm-chart/1.3.1 -m "Version 1.3.1"
```

At this point, GitHub Actions will build and release the chart. It can be found here:
https://github.com/astronomer/airflow/releases
