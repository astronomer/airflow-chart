import pytest

from tests.chart.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("namespace", ["abc", "123", "123abc", "123-abc"])
def test_namespace_names(namespace):
    """Test various namespace names to make sure they render correctly in templates"""
    render_chart(namespace=namespace)


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestExtraObjects:
    def test_default_chart_with_basedomain(self, kube_version):
        """Test that each template used with just baseDomain set renders."""
        docs = render_chart(kube_version=kube_version)
        assert len(docs) == 29

    def test_default_labels(self, kube_version):
        """Test that extra-objects works as default."""
        docs = render_chart(kube_version=kube_version)
        exclusions = ["release-name-postgresql", "release-name-postgresql-hl"]

        for doc in docs:
            if doc["metadata"]["name"] in exclusions:
                continue
            assert doc["metadata"]["labels"]["chart"].startswith("airflow")
            assert doc["metadata"]["labels"]["release"] == "release-name"
            assert doc["metadata"]["labels"]["tier"] == "airflow"
            assert doc["metadata"]["labels"]["heritage"] == "Helm"

        assert all(bool(x) for x in doc["metadata"]["labels"].values())

    test_tags = (
        "1",
        "2.3",
        "9.8.7",
        5,
        "asdf",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ-0.1.2.3.4.5.6.7.8.9_abcdefghijklmnopqrstuvwxyz",
    )

    @pytest.mark.parametrize("tag", test_tags, ids=test_tags)
    def test_default_chart_various_tags(self, tag, kube_version):
        """Test that everything works with various docker tags."""
        values = {
            "airflow": {
                "defaultAirflowTag": tag,
                "images": {
                    "airflow": {"tag": tag},
                    "statsd": {"tag": tag},
                    "pgbouncer": {"tag": tag},
                    "pgbouncerExporter": {"tag": tag},
                    "gitSync": {"tag": tag},
                },
                "authSidecar": {"tag": tag},
                "astronomer": {"images": {"certgenerator": {"tag": tag}}},
                "dagDeploy": {"images": {"dagServer": {"tag": tag}}},
                "gitSyncRelay": {
                    "images": {
                        "gitDaemon": {"tag": tag},
                        "gitSync": {"tag": tag},
                    }
                },
            },
        }
        docs = render_chart(kube_version=kube_version, values=values)
        assert len(docs) == 29
