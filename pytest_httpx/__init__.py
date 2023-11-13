from collections.abc import Generator
from typing import List

import httpx
import pytest
from pytest import MonkeyPatch

from pytest_httpx._httpx_mock import HTTPXMock
from pytest_httpx._httpx_internals import IteratorStream
from pytest_httpx.version import __version__

__all__ = (
    "HTTPXMock",
    "IteratorStream",
    "__version__",
)


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
) -> Generator[HTTPXMock, None, None]:
    # Ensure redirections to www hosts are handled transparently.
    missing_www = [
        f"www.{host}" for host in non_mocked_hosts if not host.startswith("www.")
    ]
    non_mocked_hosts += missing_www

    mock = HTTPXMock()

    # Mock synchronous requests
    real_handle_request = httpx.HTTPTransport.handle_request

    def mocked_handle_request(
        transport: httpx.HTTPTransport, request: httpx.Request
    ) -> httpx.Response:
        if request.url.host in non_mocked_hosts:
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
        if request.url.host in non_mocked_hosts:
            return await real_handle_async_request(transport, request)
        return await mock._handle_async_request(transport, request)

    monkeypatch.setattr(
        httpx.AsyncHTTPTransport,
        "handle_async_request",
        mocked_handle_async_request,
    )

    yield mock
    mock.reset(assert_all_responses_were_requested)
