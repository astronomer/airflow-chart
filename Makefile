.DEFAULT_GOAL := help

.PHONY: help
help: ## Print Makefile help.
	@grep -Eh '^[a-z.A-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-31s\033[0m %s\n", $$1, $$2}'

venv: ## Setup venv required for unit testing the helm chart
	virtualenv venv -p python3
	venv/bin/pip install -r tests/chart_tests/requirements.txt

charts: ## Update dependent charts
	helm dep update

.PHONY: unittest-chart
unittest-chart: charts venv ## Unittest the helm chart
	# Protip: you can modify pytest behavior like: PYTEST_ADDOPTS='-v --maxfail=1 --pdb -k 1.20' make unittest-chart
	venv/bin/python -m pytest -n auto tests/chart_tests

.PHONY: clean
clean: ## Clean build and test artifacts
	rm -rf venv
	rm -rf charts

.PHONY: update-requirements
update-requirements: ## Update all requirements.txt files
	for FILE in tests/chart_tests/requirements.in tests/functional-tests/requirements.in ; do pip-compile --generate-hashes --quiet --allow-unsafe --upgrade $${FILE} ; done ;
	-pre-commit run requirements-txt-fixer --all-files --show-diff-on-failure

.PHONY: show-containers
show-containers:
	@kubectl get pods -n "$$NAMESPACE" -o json | \
	  jq -r '.items[] | .metadata.name as $$podname | .spec.containers[] | "\($$podname) \(.name)"' | \
	  column -t

.PHONY: setup-kind
setup-kind: ## setup a kind cluster with calico
	kind create cluster --config kind-config.yaml
	kubectl apply -f https://docs.projectcalico.org/v3.8/manifests/calico.yaml
	kubectl -n kube-system set env daemonset/calico-node FELIX_IGNORELOOSERPF=true

.PHONY: install-aftest-chart
install-aftest-chart: ## install the aftest chart setup
	helm install --create-namespace -n aftest -f aftest-git-sync-relay-values.yaml --set .Values.defaultDenyNetworkPolicy=True --timeout 800s airflow .

.PHONY: upgrade-aftest-chart
upgrade-aftest-chart: ## upgrade the aftest chart setup with defaultDenyNetworkPolicy=True
	helm upgrade --create-namespace -n aftest -f aftest-git-sync-relay-values.yaml --set .Values.defaultDenyNetworkPolicy=True --timeout 800s airflow .

.PHONY: upgrade-aftest-chart-deny-false
upgrade-aftest-chart-deny-false: ## upgrade the aftest chart setup with defaultDenyNetworkPolicy=False
	helm upgrade --create-namespace -n aftest -f aftest-git-sync-relay-values.yaml --set .Values.defaultDenyNetworkPolicy=True --timeout 800s airflow .
