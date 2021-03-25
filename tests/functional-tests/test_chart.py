#!/usr/bin/env python3
"""
This file is for configuration testing Airflow images.
The Airflow image is started in Docker, configured to access an
instance of postgres, which is also running in Docker.

Testinfra is used to configuration test the image. In effect,
testinfra simplifies and provides syntactic sugar for doing
execs into a running container.
"""

import os

import docker
import pytest
import testinfra
from kubernetes import client, config
from packaging.version import parse as semantic_version

airflow_version = semantic_version(os.environ.get("AIRFLOW_VERSION"))
airflow_2 = airflow_version >= semantic_version("2.0.0")


def create_kube_client(in_cluster=False):
    """
    Load and store authentication and cluster information from kube-config
    file; if running inside a pod, use Kubernetes service account. Use that to
    instantiate Kubernetes client.
    """
    if in_cluster:
        print("Using in cluster kubernetes configuration")
        config.load_incluster_config()
    else:
        print("Using kubectl kubernetes configuration")
        config.load_kube_config()
    return client.CoreV1Api()


def test_pgbouncer_fqdn_trailing_dot(webserver):
    """ Ensure the FQDN for pgbouncer has a dot at the end
    """
    db_conn_string = webserver.check_output('env | grep AIRFLOW_CONN_AIRFLOW_DB')
    assert 'airflow-pgbouncer.airflow.svc.cluster.local.' in db_conn_string, \
        "Expected to find a trailing dot on the pgbouncer FQDN"


def test_airflow_in_path(webserver):
    """ Ensure Airflow is in PATH
    """
    assert webserver.exists('airflow'), \
        "Expected 'airflow' to be in PATH"


def test_tini_in_path(webserver):
    """ Ensure 'tini' is in PATH
    """
    assert webserver.exists('tini'), \
        "Expected 'tini' to be in PATH"


def test_entrypoint(webserver):
    """ There should be a file '/entrypoint'
    """
    assert webserver.file("/entrypoint").exists, \
        "Expected to find /entrypoint"


def test_elasticsearch_version(webserver):
    """ Astronomer runs a version of ElasticSearch that requires
    our users to run the client code of version 5.5.3 or greater
    """
    try:
        elasticsearch_module = webserver.pip_package.get_packages()['elasticsearch']
    except KeyError:
        raise Exception("elasticsearch pip module is not installed")
    version = elasticsearch_module['version']
    assert semantic_version(version) >= semantic_version('5.5.3'), \
        "elasticsearch module must be version 5.5.3 or greater"


@pytest.mark.skipif(airflow_2, reason="Not needed for Airflow>=2")
def test_werkzeug_version(webserver):
    """ Werkzeug pip module version >= 1.0.0 has an issue
    """
    try:
        werkzeug_module = webserver.pip_package.get_packages()['Werkzeug']
    except KeyError:
        raise Exception("Werkzeug pip module is not installed")
    version = werkzeug_module['version']
    assert semantic_version(version) < semantic_version('1.0.0'), \
        "Werkzeug pip module version must be less than 1.0.0"


def test_redis_version(webserver):
    """ Redis pip module version 3.4.0 has an issue in the Astronomer platform
    """
    try:
        redis_module = webserver.pip_package.get_packages()['redis']
    except KeyError:
        raise Exception("redis pip module is not installed")
    version = redis_module['version']
    assert semantic_version(version) != semantic_version('3.4.0'), \
        "redis module must not be 3.4.0"


def test_astronomer_airflow_check_version(webserver):
    """ astronomer-airflow-version-check 1.0.0 has an issue in the Astronomer platform
    """
    try:
        version_check_module = webserver.pip_package.get_packages()['astronomer-airflow-version-check']
    except KeyError:
        print("astronomer-airflow-version-check pip module is not installed")
        return
    version = version_check_module['version']
    assert semantic_version(version) >= semantic_version('1.0.1'), \
        "astronomer-airflow-version-check module must be greater than 1.0.0"


def test_airflow_connections(scheduler):
    """Test Connections can be added and deleted"""
    test_conn_uri = "postgresql://postgres_user:postgres_test@1.1.1.1:5432"
    test_conn_id = "test"

    if airflow_2:
        # Assert Connection can be added
        assert f"Successfully added `conn_id`={test_conn_id} : {test_conn_uri}" in scheduler.check_output(
            'airflow connections add --conn-uri %s %s', test_conn_uri, test_conn_id)

        # Assert Connection can be removed
        assert f"Successfully deleted connection with `conn_id`={test_conn_id}" in scheduler.check_output(
            'airflow connections delete %s', test_conn_id)
    else:
        # Assert Connection can be added
        assert f"Successfully added `conn_id`={test_conn_id} : {test_conn_uri}" in scheduler.check_output(
            'airflow connections -a --conn_uri %s --conn_id %s', test_conn_uri, test_conn_id)

        # Assert Connection can be removed
        assert f"Successfully deleted `conn_id`={test_conn_id}" in scheduler.check_output(
            'airflow connections -d --conn_id %s', test_conn_id)


def test_airflow_variables(scheduler):
    """Test Variables can be added, retrieved and deleted"""
    if airflow_2:
        # Assert Variables can be added
        assert "" in scheduler.check_output("airflow variables set test_key test_value")

        # Assert Variables can be retrieved
        assert "test_value" in scheduler.check_output("airflow variables get test_key")

        # Assert Variables can be deleted
        assert "" in scheduler.check_output("airflow variables delete test_key")
    else:
        # Assert Variables can be added
        assert "" in scheduler.check_output("airflow variables --set test_key test_value")

        # Assert Variables can be retrieved
        assert "test_value" in scheduler.check_output("airflow variables --get test_key")

        # Assert Variables can be deleted
        assert "" in scheduler.check_output("airflow variables --delete test_key")


@pytest.fixture(scope='session')
def webserver(request):
    """ This is the host fixture for testinfra. To read more, please see
    the testinfra documentation:
    https://testinfra.readthedocs.io/en/latest/examples.html#test-docker-images
    """
    namespace = os.environ.get('NAMESPACE')
    if not namespace:
        print("NAMESPACE env var is not present, using 'airflow' namespace")
        namespace = 'airflow'
    kube = create_kube_client()
    pods = kube.list_namespaced_pod(namespace, label_selector=f"component=webserver")
    pods = pods.items
    assert len(pods) > 0, "Expected to find at least one pod with label 'component: webserver'"
    pod = pods[0]
    yield testinfra.get_host(f'kubectl://{pod.metadata.name}?container=webserver&namespace={namespace}')


@pytest.fixture(scope='session')
def scheduler(request):
    """ This is the host fixture for testinfra. To read more, please see
    the testinfra documentation:
    https://testinfra.readthedocs.io/en/latest/examples.html#test-docker-images
    """
    namespace = os.environ.get('NAMESPACE')
    if not namespace:
        print("NAMESPACE env var is not present, using 'airflow' namespace")
        namespace = 'airflow'
    kube = create_kube_client()
    pods = kube.list_namespaced_pod(namespace, label_selector=f"component=scheduler")
    pods = pods.items
    assert len(pods) > 0, "Expected to find at least one pod with label 'component: scheduler'"
    pod = pods[0]
    yield testinfra.get_host(f'kubectl://{pod.metadata.name}?container=scheduler&namespace={namespace}')


@pytest.fixture(scope='session')
def docker_client(request):
    """ This is a text fixture for the docker client,
    should it be needed in a test
    """
    client = docker.from_env()
    yield client
    client.close()
