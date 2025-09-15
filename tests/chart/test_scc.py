import pytest

from tests import supported_k8s_versions
from tests.utils.chart import render_chart


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestAirflowSccPrivileges:
    def test_scc_privileges_defaults(self, kube_version):
        """Test airflow scc privileges with defaults - disabled."""
        docs = render_chart(
            kube_version=kube_version,
            values={},
            show_only="templates/airflow-scc-anyuid.yaml",
        )
        assert len(docs) == 0

    def test_scc_privileges_enabled(self, kube_version):
        """Test airflow scc privileges with defaults - disabled."""
        docs = render_chart(
            kube_version=kube_version,
            values={"sccEnabled": True},
            show_only="templates/airflow-scc-anyuid.yaml",
        )
        assert len(docs) == 1
        assert docs[0]["kind"] == "SecurityContextConstraints"
        assert docs[0]["apiVersion"] == "security.openshift.io/v1"
        assert docs[0]["metadata"]["name"] == "release-name-anyuid"
        assert docs[0]["users"] == [
            "system:serviceaccount:default:default",
            "system:serviceaccount:default:release-name-airflow-webserver",
            "system:serviceaccount:default:release-name-airflow-redis",
            "system:serviceaccount:default:release-name-airflow-flower",
            "system:serviceaccount:default:release-name-airflow-scheduler",
            "system:serviceaccount:default:release-name-airflow-statsd",
            "system:serviceaccount:default:release-name-airflow-create-user-job",
            "system:serviceaccount:default:release-name-airflow-migrate-database-job",
            "system:serviceaccount:default:release-name-airflow-worker",
            "system:serviceaccount:default:release-name-airflow-triggerer",
            "system:serviceaccount:default:release-name-airflow-pgbouncer",
            "system:serviceaccount:default:release-name-airflow-cleanup",
            "system:serviceaccount:default:release-name-airflow-dag-processor",
        ]
