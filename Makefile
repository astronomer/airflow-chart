.DEFAULT_GOAL := help

.PHONY: help
help: ## Print Makefile help.
	@grep -Eh '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

venv: ## Setup venv required for unit testing the helm chart
	[ -d venv ] || virtualenv venv -p python3
	venv/bin/pip install -r tests/chart_tests/requirements.txt

charts: ## Update dependent charts
	helm dep update

.PHONY: unittest-chart
unittest-chart: charts venv ## Unittest the helm chart
	venv/bin/python -m pytest -n auto tests/chart_tests

.PHONY: clean
clean: ## Clean build and test artifacts
	rm -rf venv

.PHONY: update-requirements
update-requirements: ## Update all requirements.txt files
	# Once we hit python 3.9 we should go back to using --generate-hashes
	for FILE in tests/chart_tests/requirements.in tests/functional-tests/requirements.in ; do pip-compile --quiet --allow-unsafe --upgrade $${FILE} ; done ;
	-pre-commit run requirements-txt-fixer --all-files --show-diff-on-failure
