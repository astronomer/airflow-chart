#!/usr/bin/env python3
"""This script is used to create the circle config file so that we can stay
DRY."""
from pathlib import Path
import yaml

from jinja2 import Template

git_root_dir = next(
    iter([x for x in Path(__file__).resolve().parents if (x / ".git").is_dir()]), None
)
metadata = yaml.safe_load((git_root_dir / "metadata.yaml").read_text())
kube_versions = metadata["test_k8s_versions"]

executors = ["CeleryExecutor", "LocalExecutor", "KubernetesExecutor"]
machine_image_version = "ubuntu-2204:2024.05.1"
ci_runner_version = "2024-09"


def main():
    """Render the Jinja2 template file."""
    config_file_template_path = git_root_dir / ".circleci" / "config.yml.j2"
    config_file_path = git_root_dir / ".circleci" / "config.yml"

    templated_file_content = Path(config_file_template_path).read_text()
    template = Template(templated_file_content)
    config = template.render(
        kube_versions=kube_versions,
        executors=executors,
        machine_image_version=machine_image_version,
        ci_runner_version=ci_runner_version,
    )
    with open(config_file_path, "w") as circle_ci_config_file:
        warning_header = (
            "# Warning: automatically generated file\n"
            + "# Please edit config.yml.j2, and use the script generate_circleci_config.py\n"
        )
        circle_ci_config_file.write(warning_header)
        circle_ci_config_file.write(config)
        circle_ci_config_file.write("\n")


if __name__ == "__main__":
    main()
