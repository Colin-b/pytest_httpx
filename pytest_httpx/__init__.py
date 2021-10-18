from typing import List

import httpx
import pytest

from pytest_httpx._httpx_mock import (
    HTTPXMock,
    _PytestSyncTransport,
    _PytestAsyncTransport,
)
from pytest_httpx.version import __version__


@pytest.fixture
def assert_all_responses_were_requested() -> bool:
    return True


@pytest.fixture
def non_mocked_hosts() -> list:
    return []


@pytest.fixture
def httpx_mock(
    monkeypatch, assert_all_responses_were_requested: bool, non_mocked_hosts: List[str]
) -> HTTPXMock:
    # Ensure redirections to www hosts are handled transparently.
    missing_www = [
        f"www.{host}" for host in non_mocked_hosts if not host.startswith("www.")
    ]
    non_mocked_hosts += missing_www

    mock = HTTPXMock()

    # Mock synchronous requests
    real_sync_transport = httpx.Client._transport_for_url
    monkeypatch.setattr(
        httpx.Client,
        "_transport_for_url",
        lambda self, url: real_sync_transport(self, url)
        if url.host in non_mocked_hosts
        else _PytestSyncTransport(mock),
    )
    # Mock asynchronous requests
    real_async_transport = httpx.AsyncClient._transport_for_url
    monkeypatch.setattr(
        httpx.AsyncClient,
        "_transport_for_url",
        lambda self, url: real_async_transport(self, url)
        if url.host in non_mocked_hosts
        else _PytestAsyncTransport(mock),
    )
    yield mock
    mock.reset(assert_all_responses_were_requested)
