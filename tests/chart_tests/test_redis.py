import pytest

from tests.chart_tests.helm_template_generator import render_chart

from .. import supported_k8s_versions


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestRedis:
    def test_redis_sts_defaults(self, kube_version):
        """Test Redis statefulSet defaults"""
        # TODO: find a way to use show-only with subchart
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "executor": "CeleryExecutor",
                },
            },
        )

        # workaround to find the redis sts from the subchart since we can't use --show-only
        redis_sts = [
            x
            for x in docs
            if x["kind"] == "StatefulSet"
            and x["metadata"]["name"] == "release-name-redis"
        ][0]
        assert redis_sts["spec"]["template"]["spec"]["securityContext"] == {
            "runAsUser": 0
        }

    def test_redis_sts_securityContext(self, kube_version):
        """Test Redis statefulSet with securityContext defined"""
        docs = render_chart(
            kube_version=kube_version,
            values={
                "airflow": {
                    "executor": "CeleryExecutor",
                    "redis": {"securityContext": {"fsGroup": 5000}},
                },
            },
        )
        redis_sts = [
            x
            for x in docs
            if x["kind"] == "StatefulSet"
            and x["metadata"]["name"] == "release-name-redis"
        ][0]
        assert (
            redis_sts["spec"]["template"]["spec"]["securityContext"]["fsGroup"] == 5000
        )
