# Testing

This project uses the [helm-unittest project](https://github.com/quintush/helm-unittest) to test the helm charts included within. Once that plugin is installed, you can run tests with `helm unitest -3 .`

## Writing tests

Tests should be written with one test file per template file. When writing tests, you need to find content to make assertions against. The best way to do this is something like:

```sh
helm template . \
  --set pgbouncer.enabled=True \
  --set networkPolicies.enabled=True \
  --set pgbouncer.networkPolicies.enabled=True \
  --show-only templates/pgbouncer/pgbouncer-networkpolicy.yaml
```

Which produces the following output:

```yaml
---
# Source: airflow/templates/pgbouncer/pgbouncer-networkpolicy.yaml
################################
## Pgbouncer NetworkPolicy
#################################
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: RELEASE-NAME-pgbouncer-policy
  labels:
    tier: airflow
    component: airflow-pgbouncer-policy
    release: RELEASE-NAME
    chart: "airflow-0.19.0-rc1"
    heritage: Helm
spec:
  podSelector:
    matchLabels:
      tier: airflow
      component: pgbouncer
      release: RELEASE-NAME
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          tier: airflow
          release: RELEASE-NAME
    ports:
    - protocol: TCP
      port: 6543
```

From this output, we can make the following assertions:

```yaml
---
suite: Test templates/pgbouncer/pgbouncer-networkpolicy.yaml
templates:
  - templates/pgbouncer/pgbouncer-networkpolicy.yaml
tests:
  - it: "should work with pgbouncer.enabled: True, networkPolicies.enabled: True, pgbouncer.networkPolicies.enabled: True"
    set:
      pgbouncer.enabled: True
      networkPolicies.enabled: True
      pgbouncer.networkPolicies.enabled: True
    asserts:
      - hasDocuments:
          count: 1
      - isKind:
          of: NetworkPolicy
```

With that one test case written, we can do this again with different parameters and create a new test case:

```sh
helm template . \
  --set pgbouncer.enabled=True \
  --set networkPolicies.enabled=True \
  --set pgbouncer.networkPolicies.enabled=False \
  --show-only templates/pgbouncer/pgbouncer-networkpolicy.yaml
```

Which produces:

```yaml
---
# Source: airflow/templates/pgbouncer/pgbouncer-networkpolicy.yaml
################################
## Pgbouncer NetworkPolicy
#################################
```

With that empty content, there's pretty much only one thing we can do, which is to essentially assert that it is empty:

```yaml
  - it: "should work with pgbouncer.enabled: True, networkPolicies.enabled: True, pgbouncer.networkPolicies.enabled: False"
    set:
      pgbouncer.enabled: True
      networkPolicies.enabled: True
      pgbouncer.networkPolicies.enabled: False
    asserts:
      - hasDocuments:
          count: 0
```

This is a little counterintuitive because the output has one yaml document, but there is no parseable content inside of it, so this is seen as 0 documents that would be relevant to kubernetes. If we try to assert that there is 1 document, we see the following helpful error:

```
$ helm unittest -3 .

### Chart [ airflow ] .

 FAIL  Test templates/pgbouncer/pgbouncer-networkpolicy.yaml	tests/pgbouncer_pgbouncer-networkpolicy_test.yaml
	- should work with pgbouncer.enabled: True, networkPolicies.enabled: True, pgbouncer.networkPolicies.enabled: False

		- asserts[0] `hasDocuments` fail
			Template:	airflow/templates/pgbouncer/pgbouncer-networkpolicy.yaml
			Expected documents count to be:
				1
			Actual:
				0


Charts:      1 failed, 0 passed, 1 total
Test Suites: 1 failed, 0 passed, 1 total
Tests:       1 failed, 1 passed, 2 total
Snapshot:    0 passed, 0 total
Time:        12.367064ms

Error: plugin "unittest" exited with error
```

If you do not get a useful error, there is likely something wrong other than your assertion, such as referencing the wrong template file.

## See also

- The full list of [assertion types](https://github.com/quintush/helm-unittest/blob/master/DOCUMENT.md#assertion-types)
