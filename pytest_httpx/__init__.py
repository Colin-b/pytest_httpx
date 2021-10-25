from typing import List

import pytest

from pytest_httpx._httpx_mock import to_response
from pytest_httpx._httpx_internals import IteratorStream
from pytest_httpx._router import HTTPXMock
from pytest_httpx.version import __version__


@pytest.fixture
def assert_all_responses_were_requested() -> bool:
    return True


@pytest.fixture
def non_mocked_hosts() -> list:
    return []


@pytest.fixture
def httpx_mock(assert_all_responses_were_requested: bool, non_mocked_hosts: List[str]):
    with HTTPXMock(
        assert_all_mocked=True,
        assert_all_called=assert_all_responses_were_requested,
    ) as respx_mock:
        # Pre-route non mocked hosts to pass through
        for host in non_mocked_hosts:
            if not host.startswith("www."):
                respx_mock.route(host__in=(host, f"www.{host}")).pass_through()
            else:
                respx_mock.route(host=host).pass_through()

        yield respx_mock
