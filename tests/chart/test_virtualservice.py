from subprocess import CalledProcessError

import pytest

from tests import supported_k8s_versions
from tests.utils.chart import render_chart

GATEWAY_NAME = "istio-system/default-gateway"

API_SERVER_VS = "templates/api-server/api-server-virtualservice.yaml"
WEBSERVER_VS = "templates/webserver/webserver-virtualservice.yaml"
FLOWER_VS = "templates/flower/flower-virtualservice.yaml"
DAG_SERVER_VS = "templates/dag-deploy/dag-server-virtualservice.yaml"
GIT_SYNC_RELAY_VS = "templates/git-sync-relay/git-sync-relay-virtualservice.yaml"

ALL_VS = [API_SERVER_VS, WEBSERVER_VS, FLOWER_VS, DAG_SERVER_VS, GIT_SYNC_RELAY_VS]

# The api server replaced the webserver in Airflow 3, so the two VirtualServices
# are selected by airflowVersion. The chart default (2.4.3) selects the webserver.
AIRFLOW_3 = {"airflowVersion": "3.0.0", "defaultAirflowTag": "3.0.0"}

# Each VirtualService gates on the gateway plus its own component's prerequisites.
VS_PREREQS = {
    API_SERVER_VS: {"airflow": AIRFLOW_3},
    WEBSERVER_VS: {},
    FLOWER_VS: {"airflow": {"executor": "CeleryExecutor"}},
    DAG_SERVER_VS: {"dagDeploy": {"enabled": True}},
    GIT_SYNC_RELAY_VS: {"gitSyncRelay": {"enabled": True, "repoFetchMode": "webhook"}},
}

# Backend service port used when no auth sidecar fronts the pod.
VS_BACKEND_PORT = {
    API_SERVER_VS: 8080,  # airflow.ports.apiServer
    WEBSERVER_VS: 8080,  # airflow.ports.airflowUI
    FLOWER_VS: 5555,  # airflow.ports.flowerUI
    DAG_SERVER_VS: 8000,  # dagDeploy.ports.dagServerHttp
    GIT_SYNC_RELAY_VS: 8000,  # gitSyncRelay.gitSync.webhookPort
}

AUTH_SIDECAR_PORT = 8084

VS_SERVICE_HOST = {
    API_SERVER_VS: "release-name-api-server.default.svc.cluster.local",
    WEBSERVER_VS: "release-name-webserver.default.svc.cluster.local",
    FLOWER_VS: "release-name-flower.default.svc.cluster.local",
    DAG_SERVER_VS: "release-name-dag-server.default.svc.cluster.local",
    GIT_SYNC_RELAY_VS: "release-name-git-sync-relay.default.svc.cluster.local",
}

# The three UI VirtualServices also answer on a per-release subdomain; the dag
# server and git-sync-relay are only published under the deployments host.
VS_SUBDOMAIN = {
    API_SERVER_VS: "release-name-airflow",
    WEBSERVER_VS: "release-name-airflow",
    FLOWER_VS: "release-name-flower",
}

# Ingresses that the istio gateway suppresses, with the doc count they render
# when it is disabled.
INGRESS_TEMPLATES = [
    ("templates/ingress.yaml", {"airflow": {"executor": "CeleryExecutor"}}, 2),
    ("templates/dag-deploy/dag-server-ingress.yaml", {"dagDeploy": {"enabled": True}}, 1),
    (
        "templates/git-sync-relay/git-sync-relay-ingress.yaml",
        {"gitSyncRelay": {"enabled": True, "repoFetchMode": "webhook"}},
        1,
    ),
]


def _merge(base: dict, overrides: dict) -> dict:
    """Recursively merge overrides into a copy of base."""
    merged = {key: dict(value) if isinstance(value, dict) else value for key, value in base.items()}
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def vs_values(template: str, **overrides) -> dict:
    """Values that render `template`: ingress and the istio gateway enabled, plus
    whatever component prerequisites that particular VirtualService gates on."""
    base = {
        "ingress": {"enabled": True, "baseDomain": "example.com"},
        "global": {"istio": {"gateway": {"enabled": True, "name": GATEWAY_NAME}}},
    }
    return _merge(_merge(base, VS_PREREQS[template]), overrides)


def render_vs(template: str, kube_version: str, **overrides) -> list:
    """Render a single VirtualService.

    validate_objects is off because VirtualService is an istio CRD — the cached
    schemas under tests/k8s_schema/ only cover built-in kinds, so validation
    would try (and fail) to fetch a schema for it from kubernetes-json-schema.
    """
    return render_chart(
        kube_version=kube_version,
        show_only=template,
        values=vs_values(template, **overrides),
        validate_objects=False,
    )


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestVirtualService:
    @pytest.mark.parametrize("template", ALL_VS)
    def test_virtualservice_renders_when_gateway_enabled(self, kube_version, template):
        """Each VirtualService renders and attaches to the configured gateway."""
        docs = render_vs(template, kube_version)

        assert len(docs) == 1
        doc = docs[0]
        assert doc["kind"] == "VirtualService"
        assert doc["apiVersion"] == "networking.istio.io/v1"
        assert doc["spec"]["gateways"] == [GATEWAY_NAME]
        assert doc["metadata"]["labels"]["release"] == "release-name"
        assert doc["metadata"]["labels"]["tier"] == "airflow"

    @pytest.mark.parametrize("template", ALL_VS)
    def test_virtualservice_absent_when_gateway_disabled(self, kube_version, template):
        """No VirtualServices without global.istio.gateway.enabled - the default."""
        docs = render_vs(template, kube_version, **{"global": {"istio": {"gateway": {"enabled": False}}}})

        assert docs == []

    @pytest.mark.parametrize("template", ALL_VS)
    def test_virtualservice_absent_when_ingress_disabled(self, kube_version, template):
        """ingress.enabled still gates routing, gateway or not."""
        docs = render_vs(template, kube_version, ingress={"enabled": False})

        assert docs == []

    @pytest.mark.parametrize("template", ALL_VS)
    def test_gateway_name_required_when_gateway_enabled(self, kube_version, template):
        """An enabled gateway with no name fails the render rather than emitting
        a VirtualService attached to nothing."""
        with pytest.raises(CalledProcessError) as excinfo:
            render_vs(template, kube_version, **{"global": {"istio": {"gateway": {"name": ""}}}})

        stderr = excinfo.value.stderr.decode("utf-8")
        assert "global.istio.gateway.name is required" in stderr

    @pytest.mark.parametrize("template,prereqs,ingress_count", INGRESS_TEMPLATES)
    def test_ingress_suppressed_when_gateway_enabled(self, kube_version, template, prereqs, ingress_count):
        """The Ingress and its VirtualService are mutually exclusive, so the same
        hosts are never routed twice."""
        values = _merge({"ingress": {"enabled": True, "baseDomain": "example.com"}}, prereqs)

        without_gateway = render_chart(kube_version=kube_version, show_only=template, values=values)
        assert len(without_gateway) == ingress_count
        assert all(doc["kind"] == "Ingress" for doc in without_gateway)

        with_gateway = render_chart(
            kube_version=kube_version,
            show_only=template,
            values=_merge(values, {"global": {"istio": {"gateway": {"enabled": True, "name": GATEWAY_NAME}}}}),
        )
        assert with_gateway == []

    def test_webserver_and_api_server_virtualservices_are_mutually_exclusive(self, kube_version):
        """Exactly one of the two UI VirtualServices renders, chosen by
        airflowVersion - so Airflow 2.x is not left with no route at all."""
        airflow_2 = render_chart(
            kube_version=kube_version,
            show_only=[API_SERVER_VS, WEBSERVER_VS],
            values=vs_values(WEBSERVER_VS),
            validate_objects=False,
        )
        assert [doc["metadata"]["name"] for doc in airflow_2] == ["release-name-webserver-virtualservice"]

        airflow_3 = render_chart(
            kube_version=kube_version,
            show_only=[API_SERVER_VS, WEBSERVER_VS],
            values=vs_values(API_SERVER_VS),
            validate_objects=False,
        )
        assert [doc["metadata"]["name"] for doc in airflow_3] == ["release-name-api-server-virtualservice"]

    @pytest.mark.parametrize("template", ALL_VS)
    def test_destination_is_the_backend_service_port(self, kube_version, template):
        """Without an auth sidecar, traffic goes to the component's own port.
        Istio needs a number here even though the Ingress uses a port name."""
        docs = render_vs(template, kube_version)

        destination = docs[0]["spec"]["http"][0]["route"][0]["destination"]
        assert destination["host"] == VS_SERVICE_HOST[template]
        assert destination["port"]["number"] == VS_BACKEND_PORT[template]

    @pytest.mark.parametrize("template", ALL_VS)
    def test_destination_is_the_auth_proxy_port_with_auth_sidecar(self, kube_version, template):
        """With the auth sidecar, every VirtualService targets the proxy instead."""
        docs = render_vs(template, kube_version, authSidecar={"enabled": True})

        destination = docs[0]["spec"]["http"][0]["route"][0]["destination"]
        assert destination["host"] == VS_SERVICE_HOST[template]
        assert destination["port"]["number"] == AUTH_SIDECAR_PORT

    @pytest.mark.parametrize("template", [API_SERVER_VS, WEBSERVER_VS, FLOWER_VS])
    @pytest.mark.parametrize("auth_sidecar", [True, False])
    def test_ui_virtualservices_never_rewrite(self, kube_version, template, auth_sidecar):
        """Airflow's base_url and flower's prefix already carry /<release>/..., so
        the path must reach the backend untouched in both auth modes."""
        docs = render_vs(template, kube_version, authSidecar={"enabled": auth_sidecar})

        assert "rewrite" not in docs[0]["spec"]["http"][0]

    @pytest.mark.parametrize(
        "template,prefix",
        [(DAG_SERVER_VS, "dags"), (GIT_SYNC_RELAY_VS, "git_sync")],
    )
    def test_prefix_stripped_when_routing_straight_to_backend(self, kube_version, template, prefix):
        """The Ingress leans on the NGINX controller's rewrite-target to strip the
        prefix; an istio gateway will not, so the VirtualService does it. Mirrors
        the auth sidecar's `rewrite ^/<release>/<prefix>(.*)$ $1`."""
        docs = render_vs(template, kube_version)

        rewrite = docs[0]["spec"]["http"][0]["rewrite"]["uriRegexRewrite"]
        assert rewrite["match"] == f"^/release-name/{prefix}/?(.*)$"
        assert rewrite["rewrite"] == "/\\1"

    @pytest.mark.parametrize(
        "template,prefix",
        [(DAG_SERVER_VS, "dags"), (GIT_SYNC_RELAY_VS, "git_sync")],
    )
    def test_no_rewrite_when_auth_sidecar_strips_the_prefix(self, kube_version, template, prefix):
        """The sidecar's nginx already strips the prefix, so rewriting here too
        would strip it twice."""
        docs = render_vs(template, kube_version, authSidecar={"enabled": True})

        http = docs[0]["spec"]["http"][0]
        assert "rewrite" not in http
        assert http["match"][0]["uri"]["prefix"] == f"/release-name/{prefix}"

    def test_dag_server_endpoint_allowlist_is_preserved(self, kube_version):
        """The Ingress path regex only exposes three dag server endpoints. Losing
        that when translating to istio would expose the whole dag server."""
        docs = render_vs(DAG_SERVER_VS, kube_version)

        for match in docs[0]["spec"]["http"][0]["match"]:
            assert match["uri"]["regex"] == "/release-name/dags/(upload|downloads|healthz)(/.*)?"

    @pytest.mark.parametrize("auth_sidecar,expected", [(True, "/release-name/flower"), (False, "/release-name/flower/")])
    def test_flower_prefix_trailing_slash_follows_auth_mode(self, kube_version, auth_sidecar, expected):
        """The auth proxy serves the prefix without a trailing slash; flower
        itself needs one. Same split the Ingress expresses as two path entries."""
        docs = render_vs(FLOWER_VS, kube_version, authSidecar={"enabled": auth_sidecar})

        deployments_match = docs[0]["spec"]["http"][0]["match"][0]
        assert deployments_match["authority"]["exact"] == "deployments.example.com"
        assert deployments_match["uri"]["prefix"] == expected

    @pytest.mark.parametrize("template", [API_SERVER_VS, WEBSERVER_VS, FLOWER_VS])
    def test_ui_virtualservice_hosts_and_authority_matches_stay_in_step(self, kube_version, template):
        """The deployments host serves the component only under the per-release
        prefix; the per-release host serves it at the root."""
        docs = render_vs(template, kube_version)
        spec = docs[0]["spec"]

        subdomain = f"{VS_SUBDOMAIN[template]}.example.com"
        assert spec["hosts"] == ["deployments.example.com", subdomain]

        matches = spec["http"][0]["match"]
        assert [match["authority"]["exact"] for match in matches] == spec["hosts"]
        # Prefix-scoped on the deployments host, unscoped on the per-release host.
        assert "uri" in matches[0]
        assert "uri" not in matches[1]

    @pytest.mark.parametrize("template", [API_SERVER_VS, WEBSERVER_VS, FLOWER_VS])
    def test_ui_virtualservice_global_base_domain_dual_hosts(self, kube_version, template):
        """CP HA: globalBaseDomain adds a parallel host and a parallel match."""
        docs = render_vs(
            template,
            kube_version,
            ingress={"baseDomain": "dp1.cp1.example.com", "globalBaseDomain": "dp1.cp.example.com"},
        )
        spec = docs[0]["spec"]

        subdomain = VS_SUBDOMAIN[template]
        assert spec["hosts"] == [
            "deployments.dp1.cp1.example.com",
            f"{subdomain}.dp1.cp1.example.com",
            "deployments.dp1.cp.example.com",
            f"{subdomain}.dp1.cp.example.com",
        ]
        assert [match["authority"]["exact"] for match in spec["http"][0]["match"]] == spec["hosts"]

    def test_dag_server_global_base_domain_dual_hosts(self, kube_version):
        """The dag server gets the global parent host too, but no per-release one."""
        docs = render_vs(
            DAG_SERVER_VS,
            kube_version,
            ingress={"baseDomain": "dp1.cp1.example.com", "globalBaseDomain": "dp1.cp.example.com"},
        )
        spec = docs[0]["spec"]

        assert spec["hosts"] == ["deployments.dp1.cp1.example.com", "deployments.dp1.cp.example.com"]
        assert [match["authority"]["exact"] for match in spec["http"][0]["match"]] == spec["hosts"]

    def test_git_sync_relay_is_only_published_on_the_deployments_host(self, kube_version):
        """Matching the Ingress, the webhook receiver is not published under
        globalBaseDomain."""
        docs = render_vs(
            GIT_SYNC_RELAY_VS,
            kube_version,
            ingress={"baseDomain": "dp1.cp1.example.com", "globalBaseDomain": "dp1.cp.example.com"},
        )

        assert docs[0]["spec"]["hosts"] == ["deployments.dp1.cp1.example.com"]

    def test_git_sync_relay_virtualservice_requires_webhook_fetch_mode(self, kube_version):
        """Nothing to route when git-sync-relay polls instead of receiving hooks."""
        docs = render_vs(GIT_SYNC_RELAY_VS, kube_version, gitSyncRelay={"repoFetchMode": "poll"})

        assert docs == []

    @pytest.mark.parametrize("template", ALL_VS)
    def test_virtual_service_timeout_and_retries_passthrough(self, kube_version, template):
        """global.istio.virtualService tunables land on the route."""
        retries = {"attempts": 3, "perTryTimeout": "2s"}
        docs = render_vs(
            template,
            kube_version,
            **{"global": {"istio": {"virtualService": {"timeout": "30s", "retries": retries}}}},
        )

        http = docs[0]["spec"]["http"][0]
        assert http["timeout"] == "30s"
        assert http["retries"] == retries

    @pytest.mark.parametrize("template", ALL_VS)
    def test_timeout_and_retries_omitted_by_default(self, kube_version, template):
        """Neither key is emitted unless configured, so istio's defaults apply."""
        docs = render_vs(template, kube_version)

        http = docs[0]["spec"]["http"][0]
        assert "timeout" not in http
        assert "retries" not in http

    @pytest.mark.parametrize("template", ALL_VS)
    def test_custom_gateway_name_is_used(self, kube_version, template):
        """The gateway is a pre-existing resource, referenced as namespace/name."""
        docs = render_vs(template, kube_version, **{"global": {"istio": {"gateway": {"name": "my-ns/my-gateway"}}}})

        assert docs[0]["spec"]["gateways"] == ["my-ns/my-gateway"]
