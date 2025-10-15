.DEFAULT_GOAL := help

.PHONY: help
help: ## Print Makefile help.
	@grep -Eh '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[1;36m%-25s\033[0m %s\n", $$1, $$2}'

PHONY: venv
venv: .venv ## Setup venv required for testing
.venv:
	{ uv venv -p 3.13 --seed && uv sync ; } || \
	{ python3 -m venv .venv -p python3 && .venv/bin/pip install -r tests/requirements.txt ; }

charts: ## Update dependent charts
	helm dep update

.PHONY: test
test: unittest-chart ## Run all tests

.PHONY: unittest-chart
unittest-chart: charts venv ## Unittest the helm chart
	# Protip: you can modify pytest behavior like: make unittest-chart PYTEST_ADDOPTS='-v --maxfail=1 --pdb -k "1.30 and git-sync"'
	.venv/bin/python -m pytest -n auto -v --junitxml=test-results/junit.xml tests/chart

.PHONY: clean
clean: ## Clean build and test artifacts
	rm -rf .venv
	rm -rf venv
	rm -rf charts
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -rf test-results
	find . -name __pycache__ -exec rm -rf {} \+

.PHONY: show-docker-images
show-docker-images: ## Show all docker images and versions used in the helm chart
	@helm template . 2>/dev/null \
		-f tests/enable_all_features.yaml \
		| gawk '/image: / {match($$2, /(([^"]*):[^"]*)/, a) ; printf "https://%s %s\n", a[2], a[1] ;}' | sort -u | column -t

.PHONY: uv-lock-upgrade
uv-lock-upgrade: ## Upgrade dependencies in the uv.lock file.
	uv lock --upgrade

.PHONY: uv-lock-upgrade-and-sync
uv-lock-upgrade-and-sync: uv-lock-upgrade ## Upgrade uv lockfile dependencies and sync venv
	uv sync

.PHONY: update-requirements
update-requirements: uv-lock-upgrade ## Update requirements.txt file
	uv export --format requirements-txt > tests/requirements.txt
	-pre-commit run requirements-txt-fixer --all-files --show-diff-on-failure
