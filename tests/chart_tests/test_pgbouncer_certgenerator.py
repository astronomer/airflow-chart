import jmespath
import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions

expected_rbac = {
    "apiGroups": [""],
    "resources": ["secrets"],
    "verbs": ["get", "watch", "list", "create", "patch", "delete"],
}


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestPgbouncersslFeature:
    def test_pgbouncer_certgenerator_defaults(self, kube_version):
        """Test pgbouncer cert generator defaults."""
        docs = render_chart(
            kube_version=kube_version,
            values={},
            show_only="templates/generate-ssl.yaml",
        )
        assert len(docs) == 0

    def test_pgbouncer_certgenerator_with_sslmode_enabled(self, kube_version):
        """Test pgbouncer certgenerator sslmode opts result."""
        docs = render_chart(
            kube_version=kube_version,
            values={"airflow": {"pgbouncer": {"enabled": True, "sslmode": "require"}}},
            show_only="templates/generate-ssl.yaml",
        )
        assert len(docs) == 4
        assert "ServiceAccount" == jmespath.search("kind", docs[0])
        assert "Role" == jmespath.search("kind", docs[1])
        assert expected_rbac in docs[1]["rules"]
        assert "RoleBinding" == jmespath.search("kind", docs[2])
        assert docs[3]["spec"]["template"]["spec"]["affinity"] == {}

    def test_pgbouncer_certgenerator_with_custom_registry_secret(self, kube_version):
        """Test pgbouncer certgenerator sslmode opts result."""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "registry": {"secretName": "gscsecret"},
                    "pgbouncer": {"enabled": True, "sslmode": "require"},
                }
            },
            show_only="templates/generate-ssl.yaml",
        )
        assert len(docs) == 4
        assert [{"name": "gscsecret"}] == docs[3]["spec"]["template"]["spec"][
            "imagePullSecrets"
        ]

    def test_pgbouncer_certgenerator_pgbouncerssl_extraannotations(self, kube_version):
        """Test that certgenerator.extraAnnotations correctly inserts the annotations."""
        extraAnnotations = {"test": "test"}
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "pgbouncer": {
                        "enabled": True,
                        "sslmode": "require",
                    }
                },
                "certgenerator": {
                    "extraAnnotations": extraAnnotations,
                },
            },
            show_only="templates/generate-ssl.yaml",
        )
        assert len(docs) == 4
        assert (
            docs[3]["spec"]["template"]["metadata"]["annotations"] == extraAnnotations
        )

    def test_pgbouncer_certgenerator_pgbouncerssl_affinity(self, kube_version):
        """Test that certgenerator.affinity correctly inserts the affinity."""
        affinity = {
            "nodeAffinity": {
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "foo",
                                    "operator": "In",
                                    "values": ["bar", "baz"],
                                }
                            ]
                        }
                    ]
                }
            }
        }
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "pgbouncer": {
                        "enabled": True,
                        "sslmode": "require",
                    }
                },
                "certgenerator": {
                    "affinity": affinity,
                },
            },
            show_only="templates/generate-ssl.yaml",
        )
        assert len(docs) == 4
        assert docs[3]["spec"]["template"]["spec"]["affinity"] == affinity
