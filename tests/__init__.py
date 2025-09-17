from pathlib import Path

import yaml

# The top-level path of this repository
git_root_dir = next(iter([x for x in Path(__file__).resolve().parents if (x / ".git").is_dir()]), None)

metadata = yaml.safe_load((git_root_dir / "metadata.yaml").read_text())
# replace all patch versions with 0 so we end up with ['a.b.0', 'x.y.0']
supported_k8s_versions = [".".join([*x.split(".")[:-1], "0"]) for x in metadata["test_k8s_versions"]]


def container_env_to_dict(container):
    """Return a dict of a k8s container env structure.

    This only works with serializable env structures, and will error if the env is not serializable.
    """
    return {env["name"]: env["value"] for env in container["env"]}

def get_all_features():
    return yaml.safe_load((Path(__file__).parent.parent / "enable_all_features.yaml").read_text())