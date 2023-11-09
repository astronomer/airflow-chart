#!/usr/bin/env python3
"""This script is used to create the circle config file so that we can stay
DRY."""
import os
from pathlib import Path

from jinja2 import Template

# When adding a new version, look up the most recent patch version on Dockerhub
# https://hub.docker.com/r/kindest/node/tags
# This should match what is in tests/__init__.py
kube_versions = [
    "1.24.15",
    "1.25.11",
    "1.26.6",
    "1.27.3",
]

# https://circleci.com/docs/2.0/building-docker-images/#docker-version
remote_docker_version = "20.10.24"

executors = ["CeleryExecutor", "LocalExecutor", "KubernetesExecutor"]
ci_runner_version = "2023-11"


def main():
    """Render the Jinja2 template file."""
    circle_directory = os.path.dirname(os.path.realpath(__file__))
    config_template_path = os.path.join(circle_directory, "config.yml.j2")
    config_path = os.path.join(circle_directory, "config.yml")

    templated_file_content = Path(config_template_path).read_text()
    template = Template(templated_file_content)
    config = template.render(
        kube_versions=kube_versions,
        executors=executors,
        ci_runner_version=ci_runner_version,
        remote_docker_version=remote_docker_version,
    )
    with open(config_path, "w") as circle_ci_config_file:
        warning_header = (
            "# Warning: automatically generated file\n"
            + "# Please edit config.yml.j2, and use the script generate_circleci_config.py\n"
        )
        circle_ci_config_file.write(warning_header)
        circle_ci_config_file.write(config)
        circle_ci_config_file.write("\n")


if __name__ == "__main__":
    main()
