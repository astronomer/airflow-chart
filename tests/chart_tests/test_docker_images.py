import docker
import jmespath
import pytest

from tests.chart_tests.conftest import docker_daemon_present
from tests.chart_tests.helm_template_generator import render_chart


def list_docker_images():

    charts = render_chart()
    search_string = "spec.template.spec.containers[*].image"

    # Listing docker images
    docker_images = []
    for chart in charts:
        docker_image_sublist = jmespath.search(search_string, chart)

        if docker_image_sublist is not None:
            docker_images = docker_image_sublist + docker_images

    return docker_images


@pytest.mark.parametrize("docker_image", list_docker_images())
@pytest.mark.skipif(not docker_daemon_present(), reason="Docker daemon not available")
@pytest.mark.flaky(reruns=5, reruns_delay=1)
def test_docker_image(docker_client, docker_image):
    docker_image = docker_image.replace('"', "").strip()
    try:
        docker_client.images.get_registry_data(docker_image)
    except docker.errors.APIError as exc:
        assert False, f"'Error reading image: {docker_image} | Error: {exc}"
