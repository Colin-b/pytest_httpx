import warnings
from collections.abc import Generator
from typing import List

import httpx
import pytest
from pytest import Config, FixtureRequest, MonkeyPatch

from pytest_httpx._httpx_mock import HTTPXMock, HTTPXMockOptions
from pytest_httpx._httpx_internals import IteratorStream
from pytest_httpx.version import __version__

__all__ = (
    "HTTPXMock",
    "IteratorStream",
    "__version__",
)


FIXTURE_DEPRECATION_MSG = """\
The assert_all_responses_were_requested and non_mocked_hosts fixtures are deprecated.
Use the following marker instead:

{options!r}
"""


@pytest.fixture
def assert_all_responses_were_requested() -> bool:
    return True


@pytest.fixture
def non_mocked_hosts() -> List[str]:
    return []


@pytest.fixture
def httpx_mock(
    monkeypatch: MonkeyPatch,
    assert_all_responses_were_requested: bool,
    non_mocked_hosts: List[str],
    request: FixtureRequest,
) -> Generator[HTTPXMock, None, None]:
    marker = request.node.get_closest_marker("httpx_mock")

    if marker:
        options = HTTPXMockOptions.from_marker(marker)
    else:
        deprecated_usage = not assert_all_responses_were_requested or non_mocked_hosts
        options = HTTPXMockOptions(
            assert_all_responses_were_requested=assert_all_responses_were_requested,
            non_mocked_hosts=non_mocked_hosts,
        )
        if deprecated_usage:
            warnings.warn(
                FIXTURE_DEPRECATION_MSG.format(options=options), DeprecationWarning
            )

    # Make sure we use options instead
    del non_mocked_hosts
    del assert_all_responses_were_requested

    mock = HTTPXMock()

    # Mock synchronous requests
    real_handle_request = httpx.HTTPTransport.handle_request

    def mocked_handle_request(
        transport: httpx.HTTPTransport, request: httpx.Request
    ) -> httpx.Response:
        if request.url.host in options.non_mocked_hosts:
            return real_handle_request(transport, request)
        return mock._handle_request(transport, request)

    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        mocked_handle_request,
    )

    # Mock asynchronous requests
    real_handle_async_request = httpx.AsyncHTTPTransport.handle_async_request

    async def mocked_handle_async_request(
        transport: httpx.AsyncHTTPTransport, request: httpx.Request
    ) -> httpx.Response:
        if request.url.host in options.non_mocked_hosts:
            return await real_handle_async_request(transport, request)
        return await mock._handle_async_request(transport, request)

    monkeypatch.setattr(
        httpx.AsyncHTTPTransport,
        "handle_async_request",
        mocked_handle_async_request,
    )

    yield mock
    mock.reset(options.assert_all_responses_were_requested)


def pytest_configure(config: Config) -> None:
    config.addinivalue_line(
        "markers",
        "httpx_mock(*, assert_all_responses_were_requested=True, "
        "non_mocked_hosts=[]): Configure httpx_mock fixture.",
    )
