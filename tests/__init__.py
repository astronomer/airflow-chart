from pathlib import Path

import git
import yaml

# The top-level path of this repository
git_repo = git.Repo(__file__, search_parent_directories=True)
git_root_dir = Path(git_repo.git.rev_parse("--show-toplevel"))

with open(f"{git_root_dir}/.circleci/config.yml") as f:
    circleci_config = yaml.safe_load(f.read())

# This should match the major.minor version list in .circleci/generate_circleci_config.py
# Patch version should always be 0
supported_k8s_versions = ["1.22.0", "1.23.0", "1.24.0", "1.25.0", "1.26.0"]
