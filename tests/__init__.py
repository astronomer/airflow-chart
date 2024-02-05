from pathlib import Path

import yaml

# The top-level path of this repository
GIT_ROOT = [x for x in Path(__file__).resolve().parents if (x / ".git").is_dir()][-1]

metadata = yaml.safe_load((Path(GIT_ROOT) / "metadata.yaml").read_text())
# replace all patch versions with 0 so we end up with ['1.26.0', '1.27.0']
supported_k8s_versions = [
    ".".join(x.split(".")[:-1] + ["0"]) for x in metadata["test_k8s_versions"]
]
