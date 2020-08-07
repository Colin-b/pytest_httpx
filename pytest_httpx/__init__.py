import httpx
import pytest

from pytest_httpx._httpx_mock import (
    HTTPXMock,
    to_response,
    _PytestSyncTransport,
    _PytestAsyncTransport,
)
from pytest_httpx.version import __version__


@pytest.fixture
def assert_all_responses_were_requested() -> bool:
    return True


@pytest.fixture
def httpx_mock(monkeypatch, assert_all_responses_were_requested: bool) -> HTTPXMock:
    mock = HTTPXMock()
    # Mock synchronous requests
    monkeypatch.setattr(
        httpx.Client, "_transport_for_url", lambda self, url: _PytestSyncTransport(mock)
    )
    # Mock asynchronous requests
    monkeypatch.setattr(
        httpx.AsyncClient,
        "_transport_for_url",
        lambda self, url: _PytestAsyncTransport(mock),
    )
    yield mock
    mock.reset(assert_all_responses_were_requested)
