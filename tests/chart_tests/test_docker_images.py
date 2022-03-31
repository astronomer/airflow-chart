import docker
import jmespath
import pytest

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


# Pulling docker image test
@pytest.mark.parametrize("docker_image", list_docker_images())
def test_docker_image(docker_client, docker_image):
    docker_image = docker_image.replace('"', "").strip()
    try:
        # Pulling docker image
        docker_client.images.pull(docker_image)
    except docker.errors.APIError as exc:
        assert False, f"'Unable to pull docker image: {docker_image} | Error: {exc}"
