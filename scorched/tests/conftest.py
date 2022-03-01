import os
import socket

import pytest
import requests
from requests.exceptions import ConnectionError


def get_unused_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("localhost", 0))
    addr, port = s.getsockname()
    s.close()
    return port


def is_responsive(url):
    ping_url = f"{url}/admin/ping"
    try:
        response = requests.get(ping_url)
        if response.status_code == 200:
            return True
    except ConnectionError:
        return False


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    # This is hackish. `docker_compose_file` is
    # called before the fixture `docker_services` is
    # executed and this is the only point where
    # we could inject our own custom port into the environment.
    # Quite after usage of the `docker_services` fixture
    # the container is still started and changes in environment
    # have no effect.
    #
    # ensure that we use an unused custom port to allow
    # for multiple instances to run simultanously
    port = get_unused_port()
    os.environ["SCORCHED_TEST_SOLR_PORT"] = str(port)
    return os.path.join(
        str(pytestconfig.rootdir), "scorched", "tests", "docker-compose.yml"
    )


@pytest.fixture(scope="session")
def solr_url(docker_ip, docker_services):
    """Ensure that HTTP service is up and responsive."""
    # `port_for` takes a container port and returns the corresponding host port
    port = docker_services.port_for("solr", 8983)
    solr_url = "http://{}:{}/solr/core0".format(docker_ip, port)
    docker_services.wait_until_responsive(
        timeout=30.0, pause=1.0, check=lambda: is_responsive(solr_url)
    )
    os.environ["SOLR_URL"] = solr_url
    return solr_url
