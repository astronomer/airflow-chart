from pathlib import Path

import git
import yaml

# The top-level path of this repository
git_repo = git.Repo(__file__, search_parent_directories=True)
git_root_dir = Path(git_repo.git.rev_parse("--show-toplevel"))

with open(f"{git_root_dir}/.circleci/config.yml") as f:
    circleci_config = yaml.safe_load(f.read())

# fmt: off
supported_k8s_versions = circleci_config["workflows"]["install-airflow-chart"]["jobs"][4]["airflow-test"]["matrix"]["parameters"]["kube_version"]
# fmt: on
