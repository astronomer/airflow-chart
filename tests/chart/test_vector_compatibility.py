import io
import re
import tarfile

import docker
import pytest
import yaml

from tests.chart.conftest import docker_daemon_present
from tests.utils.chart import render_chart

# Vector 0.57+ disables `${VAR}` interpolation in config files, and ap-vector images can ship
# VECTOR_DANGEROUSLY_ALLOW_ENV_VAR_INTERPOLATION=true as a stopgap. Turn it off explicitly so
# these tests can't pass only because an image happens to enable it.
_INTERPOLATION_OFF = {"VECTOR_DANGEROUSLY_ALLOW_ENV_VAR_INTERPOLATION": "false"}
_ENVIRONMENT = {
    "COMPONENT": "worker",
    "WORKSPACE": "vector-validation",
    "RELEASE": "release-validation",
}
_ENV_TOKEN = re.compile(r"\$\{[^{}]+\}")


def _audit_environment_references(config):
    """Rendered configs must not contain any `${VAR}` reference.

    `vector validate` is not enough on its own: with interpolation disabled Vector leaves an
    unresolved `${VAR}` in place as a literal string rather than failing, so a config that
    still depends on it validates cleanly and then mislabels events / names indexes wrongly.
    """
    references = set(_ENV_TOKEN.findall(config))
    assert not references, f"Unexpected Vector environment references: {references}"


def _write_container_files(container, files):
    """Inject files/directories into a created (not-yet-started) container via the Docker API.

    We can't use host bind mounts (`volumes=` on `containers.run`) here: the
    `unittest-charts` CircleCI job runs on a `docker` executor with
    `setup_remote_docker`, which executes containers against a *separate* remote
    Docker Engine VM. Bind mounts are resolved against that remote host's
    filesystem, not the primary container where `tmp_path` actually lives, so a
    mounted directory silently shows up empty and Vector reports the config file
    as not found no matter what path it's mounted at. Shipping the file contents
    through the Docker API via `put_archive` works regardless of where the
    daemon is actually running.

    `files` maps a path (relative to `/`) to its contents as bytes, or to `None`
    to create an empty directory at that path.
    """
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        for path, content in files.items():
            info = tarfile.TarInfo(name=path.lstrip("/"))
            if content is None:
                info.type = tarfile.DIRTYPE
                # World-writable: the image may run `vector` as a non-root user
                # whose uid we don't know ahead of time, and this directory only
                # ever exists inside a throwaway validation container.
                info.mode = 0o777
                tar.addfile(info)
            else:
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))
    tar_stream.seek(0)
    container.put_archive("/", tar_stream)


def _render_sidecar(airflow_version):
    """Render the built-in logging-sidecar config; return (vector configs, sidecar image)."""
    manifests = render_chart(
        values={
            "dagDeploy": {"enabled": True},
            "loggingSidecar": {"enabled": True},
            "airflow": {
                "airflowVersion": airflow_version,
                "elasticsearch": {
                    "enabled": True,
                    "connection": {
                        "host": "elasticsearch.example.test",
                        "port": 9200,
                        "user": "vector-validation",
                        "pass": "vector-validation",
                    },
                },
            },
        }
    )

    configs = {
        config
        for manifest in manifests
        if manifest.get("kind") == "ConfigMap"
        for key, config in manifest.get("data", {}).items()
        if "vector" in key.lower() and isinstance(config, str)
    }
    assert configs, "No rendered Vector ConfigMaps found"

    images = {
        container["image"]
        for manifest in manifests
        for container in manifest.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
        if container.get("name") == "sidecar-log-consumer"
    }
    assert len(images) == 1, f"Expected one rendered logging sidecar image, found: {images}"
    return sorted(configs), images.pop()


def _ensure_image(docker_client, image):
    # `containers.create()` (unlike `containers.run()`) does not implicitly pull a
    # missing image, and CI's remote Docker Engine starts with an empty image
    # cache each run, so pull explicitly up front rather than relying on it
    # already being present.
    try:
        docker_client.images.get(image)
    except docker.errors.ImageNotFound:
        docker_client.images.pull(image)


def _run_vector(docker_client, image, config, command, environment):
    """Run `vector <command>` against `config` in a throwaway container; return (exit code, logs)."""
    container = docker_client.containers.create(
        image,
        entrypoint="vector",
        command=command,
        environment={**_INTERPOLATION_OFF, **environment},
    )
    try:
        _write_container_files(
            container,
            {
                "config/vector.yaml": yaml.safe_dump(config).encode(),
                "vector-data": None,
            },
        )
        container.start()
        status = container.wait()["StatusCode"]
        logs = container.logs(stdout=True, stderr=True).decode(errors="replace")
        return status, logs
    finally:
        container.remove(force=True)


def _validation_config(config):
    validation_config = yaml.safe_load(config)
    validation_config["data_dir"] = "/vector-data"
    validation_config["sinks"]["out"]["healthcheck"] = {"enabled": False}
    return validation_config


@pytest.mark.parametrize("airflow_version", ["2.10.5", "3.0.0"])
@pytest.mark.skipif(not docker_daemon_present(), reason="Docker daemon not available")
def test_builtin_vector_configs_validate_with_their_image(docker_client, airflow_version):
    """Validate the rendered logging-sidecar Vector config against the real, pinned `ap-vector` image.

    Vector 0.57.0 disabled `${VAR}`-style env var interpolation by default
    (PINF-1239/PINF-675), which turns a config that still relies on it into a
    crash-loop or, worse, silently mislabelled events. The sidecar config therefore
    carries no `${VAR}` references at all: pod-label metadata is read at runtime with
    VRL's `get_env_var` and the index name is templated from the event's `.release`
    field. This test fails if a `${VAR}` reference creeps back in, and runs `vector
    validate` with interpolation explicitly off so a `loggingSidecar.image` bump past
    0.57 (e.g. for a CVE fix) is exercised in CI rather than in production.
    """
    configs, image = _render_sidecar(airflow_version)
    _ensure_image(docker_client, image)

    for index, config in enumerate(configs):
        _audit_environment_references(config)
        status, logs = _run_vector(
            docker_client,
            image,
            _validation_config(config),
            command=["--require-healthy", "false", "validate", "/config/vector.yaml"],
            environment=_ENVIRONMENT,
        )
        assert status == 0, f"vector validate failed for config index {index} (exit {status}):\n{logs}"


@pytest.mark.parametrize("airflow_version", ["2.10.5", "3.0.0"])
@pytest.mark.parametrize(
    "environment, expected",
    [
        pytest.param(
            _ENVIRONMENT,
            {"component": "worker", "workspace": "vector-validation", "release": "release-validation"},
            id="labels-present",
        ),
        # A fieldRef on a pod label that doesn't exist yields an empty (set but empty) env var, e.g.
        # `workspace` on the dag-server / git-sync-relay pods unless `.Values.labels` provides it.
        pytest.param(
            {"COMPONENT": "", "WORKSPACE": "", "RELEASE": ""},
            {"component": "-", "workspace": "-", "release": "-"},
            id="labels-empty",
        ),
        pytest.param({}, {"component": "-", "workspace": "-", "release": "-"}, id="env-unset"),
    ],
)
@pytest.mark.skipif(not docker_daemon_present(), reason="Docker daemon not available")
def test_builtin_vector_config_stamps_pod_metadata_without_interpolation(docker_client, airflow_version, environment, expected):
    """The component/workspace/release fields resolve from the env at runtime, falling back to `-`.

    This is the behaviour `${COMPONENT:--}` etc. used to provide via config interpolation. It runs
    the rendered transforms through `vector test` on the real image with interpolation disabled.
    """
    (config, *_), image = _render_sidecar(airflow_version)
    _ensure_image(docker_client, image)

    validation_config = _validation_config(config)
    condition = " && ".join(f'.{field} == "{value}"' for field, value in expected.items())
    validation_config["tests"] = [
        {
            "name": f"{transform}_stamps_pod_metadata",
            "inputs": [
                {
                    "insert_at": transform,
                    "type": "vrl",
                    # A native timestamp, as the file source emits (a string would fail `parse_timestamp!`
                    # in the transform, and remap then passes the event through unchanged).
                    "source": '. = {"message": "test"}\n.@timestamp = now()',
                }
            ],
            "outputs": [
                {
                    "extract_from": transform,
                    "conditions": [{"type": "vrl", "source": condition}],
                }
            ],
        }
        for transform in ("transform_airflow_logs", "final_task_log")
    ]

    status, logs = _run_vector(
        docker_client,
        image,
        validation_config,
        command=["test", "/config/vector.yaml"],
        environment=environment,
    )
    assert status == 0, f"vector test failed (exit {status}):\n{logs}"
