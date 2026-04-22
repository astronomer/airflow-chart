import yaml

from tests import git_root_dir


def get_service_ports_by_name(doc) -> dict:
    """Given a single service doc, return all the ports by name."""

    return {port_config["name"]: port_config for port_config in doc["spec"]["ports"]}


def get_all_features() -> dict:
    return yaml.safe_load((git_root_dir / "tests" / "enable_all_features.yaml").read_text())
