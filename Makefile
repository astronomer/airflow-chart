.DEFAULT_GOAL := help

.PHONY: help
help: ## Print Makefile help.
	@grep -Eh '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

venv: ## Setup venv required for unit testing the helm chart
	virtualenv venv -p python3
	venv/bin/pip install -r tests/chart_tests/requirements.txt

charts: ## Update dependent charts
	helm dep update

.PHONY: unittest-chart
unittest-chart: charts venv ## Unittest the helm chart
	# Protip: you can modify pytest behavior like: make unittest-chart PYTEST_ADDOPTS='-v --maxfail=1 --pdb -k 1.20'
	venv/bin/python -m pytest -n auto -v --junitxml=test-results/junit.xml tests/chart_tests

.PHONY: clean
clean: ## Clean build and test artifacts
	rm -rf venv
	rm -rf charts
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -rf test-results
	find . -name __pycache__ -exec rm -rf {} \+

.PHONY: update-requirements
update-requirements: ## Update all requirements.txt files
	for FILE in tests/chart_tests/requirements.in tests/functional-tests/requirements.in ; do pip-compile --generate-hashes --quiet --allow-unsafe --upgrade $${FILE} ; done ;
	-pre-commit run requirements-txt-fixer --all-files --show-diff-on-failure

.PHONY: show-docker-images
show-docker-images: ## Show all docker images and versions used in the helm chart
	@helm template . 2>/dev/null \
		-f tests/enable_all_features.yaml \
		| gawk '/image: / {match($$2, /(([^"]*):[^"]*)/, a) ; printf "https://%s %s\n", a[2], a[1] ;}' | sort -u | column -t
