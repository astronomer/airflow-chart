import io
import re
import tarfile

import pytest
import yaml

from tests.chart.conftest import docker_daemon_present
from tests.utils.chart import render_chart

_ALLOWED_ENV_REFERENCES = {
    "${COMPONENT:--}",
    "${WORKSPACE:--}",
    "${RELEASE:--}",
}
_ENVIRONMENT = {
    "COMPONENT": "worker",
    "WORKSPACE": "vector-validation",
    "RELEASE": "release-validation",
}
_ENV_TOKEN = re.compile(r"\$\{[^{}]+\}")


def _audit_environment_references(config):
    references = set(_ENV_TOKEN.findall(config))
    unexpected_references = references - _ALLOWED_ENV_REFERENCES
    assert not unexpected_references, f"Unexpected Vector environment references: {unexpected_references}"


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
                info.mode = 0o755
                tar.addfile(info)
            else:
                info.size = len(content)
                tar.addfile(info, io.BytesIO(content))
    tar_stream.seek(0)
    container.put_archive("/", tar_stream)


@pytest.mark.parametrize("airflow_version", ["2.10.5", "3.0.0"])
@pytest.mark.skipif(not docker_daemon_present(), reason="Docker daemon not available")
def test_builtin_vector_configs_validate_with_their_image(docker_client, airflow_version):
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
    image = images.pop()

    for index, config in enumerate(configs):
        _audit_environment_references(config)
        validation_config = yaml.safe_load(config)
        validation_config["data_dir"] = "/vector-data"
        validation_config["sinks"]["out"]["healthcheck"] = {"enabled": False}
        config_bytes = yaml.safe_dump(validation_config).encode()

        container = docker_client.containers.create(
            image,
            entrypoint="vector",
            command=["--require-healthy", "false", "validate"],
            environment={
                **_ENVIRONMENT,
                "VECTOR_CONFIG": f"/config/vector-{index}.yaml",
            },
        )
        try:
            _write_container_files(
                container,
                {
                    f"config/vector-{index}.yaml": config_bytes,
                    "vector-data": None,
                },
            )
            container.start()
            result = container.wait()
            logs = container.logs(stdout=True, stderr=True).decode(errors="replace")
            assert result["StatusCode"] == 0, (
                f"vector validate failed for config index {index} (exit {result['StatusCode']}):\n{logs}"
            )
        finally:
            container.remove(force=True)
