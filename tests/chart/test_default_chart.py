import pytest

from tests import supported_k8s_versions
from tests.utils import get_all_features, get_containers_by_name
from tests.utils.chart import render_chart

exclusions = ["release-name-postgresql", "release-name-postgresql-hl"]


@pytest.mark.parametrize("namespace", ["abc", "123", "123abc", "123-abc"])
def test_namespace_names(namespace):
    """Test various namespace names to make sure they render correctly in templates"""
    render_chart(namespace=namespace)


@pytest.mark.parametrize("kube_version", supported_k8s_versions)
class TestDefaultChart:
    def test_default_chart_with_basedomain(self, kube_version):
        """Test that each template used with just baseDomain set renders."""
        docs = render_chart(kube_version=kube_version)
        assert len(docs) == 27

    def test_default_labels(self, kube_version):
        """Test that extra-objects works as default."""
        docs = render_chart(kube_version=kube_version)

        for doc in docs:
            if doc["metadata"]["name"] in exclusions:
                continue
            assert doc["metadata"]["labels"]["chart"].startswith("airflow")
            assert doc["metadata"]["labels"]["release"] == "release-name"
            assert doc["metadata"]["labels"]["tier"] == "airflow"
            assert doc["metadata"]["labels"]["heritage"] == "Helm"
            assert all(bool(x) for x in doc["metadata"]["labels"].values())


class TestReadOnlyRootFilesystem:
    chart_values = get_all_features()
    docs = render_chart(values=chart_values)
    containers = [
        container
        for doc in docs
        if doc["metadata"]["name"] not in exclusions
        for container in get_containers_by_name(doc, include_init_containers=True).items()
    ]

    @pytest.mark.parametrize("container_name,container", containers, ids=[x[0] for x in containers])
    def test_container_read_only_root_filesystem(self, container_name, container):
        """Test that all containers run with readOnlyRootFilesystem."""
        assert container.get("securityContext", {}).get("readOnlyRootFilesystem"), (
            f"Container {container_name} does not have readOnlyRootFilesystem set to true"
        )

    @pytest.mark.skip(reason="Known failures. We should circle back and fix these.")
    @pytest.mark.parametrize("container_name,container", containers, ids=[x[0] for x in containers])
    def test_container_resources(self, container_name, container):
        """Test that all containers have resources set by default."""
        assert container.get("resources"), f"Container {container_name} does not have resources set by default."

    @pytest.mark.skip(reason="Known failures. We should circle back and fix these.")
    @pytest.mark.parametrize("container_name,container", containers, ids=[x[0] for x in containers])
    def test_container_image_pull_policy(self, container_name, container):
        """Test that all containers have imagePullPolicy set to IfNotPresent by default."""
        assert container.get("imagePullPolicy") == "IfNotPresent", (
            f"Container {container_name} does not have imagePullPolicy set to IfNotPresent by default."
        )
