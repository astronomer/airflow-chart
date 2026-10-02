import re

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


@pytest.mark.parametrize("airflow_version", ["2.10.5", "3.0.0"])
@pytest.mark.skipif(not docker_daemon_present(), reason="Docker daemon not available")
def test_builtin_vector_configs_validate_with_their_image(docker_client, tmp_path, airflow_version):
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
        config_dir = tmp_path / "config"
        config_dir.mkdir(exist_ok=True)
        log_dir = tmp_path / "logs"
        log_dir.mkdir(exist_ok=True)
        config_path = config_dir / f"vector-{index}.yaml"
        validation_config = yaml.safe_load(config)
        validation_config["data_dir"] = "/vector-data"
        validation_config["sinks"]["out"]["healthcheck"] = {"enabled": False}
        config_path.write_text(yaml.safe_dump(validation_config))
        docker_client.containers.run(
            image,
            entrypoint="vector",
            command=["--require-healthy", "false", "validate"],
            environment={
                **_ENVIRONMENT,
                "VECTOR_CONFIG": f"/vector-config/vector-{index}.yaml",
            },
            volumes={
                str(config_dir): {"bind": "/vector-config", "mode": "ro"},
                str(log_dir): {"bind": "/vector-data", "mode": "rw"},
            },
            remove=True,
        )
