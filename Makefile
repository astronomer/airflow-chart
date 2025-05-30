.DEFAULT_GOAL := help

.PHONY: help
help: ## Print Makefile help.
	@grep -Eh '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[1;36m%-20s\033[0m %s\n", $$1, $$2}'

venv: ## Setup venv required for unit testing the helm chart
	uv venv venv -p 3.11 --seed || virtualenv venv -p python3
	venv/bin/pip install -r requirements/chart.txt

charts: ## Update dependent charts
	helm dep update

.PHONY: test
test: unittest-chart ## Run all tests

.PHONY: unittest-chart
unittest-chart: charts venv ## Unittest the helm chart
	# Protip: you can modify pytest behavior like: make unittest-chart PYTEST_ADDOPTS='-v --maxfail=1 --pdb -k "1.30 and git-sync"'
	venv/bin/python -m pytest -n auto -v --junitxml=test-results/junit.xml tests/chart

.PHONY: clean
clean: ## Clean build and test artifacts
	rm -rf venv
	rm -rf charts
	rm -rf .ruff_cache
	rm -rf .pytest_cache
	rm -rf test-results
	find . -name __pycache__ -exec rm -rf {} \+

.PHONY: update-requirements
update-requirements: ## Update all python requirements files
	for FILE in requirements/*.in ; do uv pip compile --quiet --generate-hashes --upgrade $${FILE} --output-file $${FILE%.in}.txt ; done ;
	-pre-commit run requirements-txt-fixer --all-files --show-diff-on-failure

.PHONY: show-docker-images
show-docker-images: ## Show all docker images and versions used in the helm chart
	@helm template . 2>/dev/null \
		-f tests/enable_all_features.yaml \
		| gawk '/image: / {match($$2, /(([^"]*):[^"]*)/, a) ; printf "https://%s %s\n", a[2], a[1] ;}' | sort -u | column -t
