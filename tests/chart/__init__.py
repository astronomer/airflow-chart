import yaml

from tests import git_root_dir


def get_containers_by_name(doc, include_init_containers=False) -> dict:
    """Given a single doc, return all the containers by name.

    doc must be a valid spec for a pod manager. (EG: ds, sts)
    """

    c_by_name = {c["name"]: c for c in doc["spec"]["template"]["spec"]["containers"]}

    if include_init_containers and doc["spec"]["template"]["spec"].get("initContainers"):
        c_by_name |= {c["name"]: c for c in doc["spec"]["template"]["spec"].get("initContainers")}

    return c_by_name


def get_service_ports_by_name(doc) -> dict:
    """Given a single service doc, return all the ports by name."""

    return {port_config["name"]: port_config for port_config in doc["spec"]["ports"]}


def get_all_features() -> dict:
    return yaml.safe_load((git_root_dir / "tests" / "enable_all_features.yaml").read_text())
