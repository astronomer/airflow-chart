from pathlib import Path

import git
import yaml

# The top-level path of this repository
git_repo = git.Repo(__file__, search_parent_directories=True)
git_root_dir = Path(git_repo.git.rev_parse("--show-toplevel"))

with open(f"{git_root_dir}/.circleci/config.yml") as f:
    circleci_config = yaml.safe_load(f.read())

# fmt: off
# Load supported versions and replace patch segment with 0
supported_k8s_versions = [
    '.'.join(zero_version_list)
    for version_str in circleci_config["workflows"]["install-airflow-chart"]["jobs"][4]["airflow-test"]["matrix"]["parameters"]["kube_version"]
    for zero_version_list in [version_str.split('.')[:2] + ['0']]
]
# fmt: on
