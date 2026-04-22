import pytest

from tests import supported_k8s_versions
from tests.utils.chart import render_chart

retention_policy_test_data = [
    {"whenDeleted": "Retain"},
    {"whenDeleted": "Delete"},
]


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
@pytest.mark.parametrize(
    "retention_policy",
    retention_policy_test_data,
    ids=[f"{key}-{value}" for rp in retention_policy_test_data for key, value in rp.items()],
)
def test_redis_persistence_retention_custom(kube_version, retention_policy):
    """Test persistence aspects"""

    values = {
        "airflow": {
            "executor": "CeleryExecutor",
            "redis": {
                "enabled": True,
                "persistence": {"enabled": True, "persistentVolumeClaimRetentionPolicy": retention_policy},
            },
        },
    }

    docs = render_chart(
        kube_version=kube_version,
        show_only="charts/airflow/templates/redis/redis-statefulset.yaml",
        values=values,
    )

    assert len(docs) == 1
    assert docs[0]["spec"]["persistentVolumeClaimRetentionPolicy"] == retention_policy
