from collections.abc import Generator
from operator import methodcaller

import pytest
from pytest import Config, FixtureRequest, MonkeyPatch

from pytest_httpx._httpx_compat import HttpxBackend, get_backends
from pytest_httpx._httpx_mock import HTTPXMock
from pytest_httpx._httpx_internals import IteratorStream
from pytest_httpx._options import _HTTPXMockOptions
from pytest_httpx.version import __version__

__all__ = (
    "HTTPXMock",
    "IteratorStream",
    "__version__",
)


def _mock_backend(
    monkeypatch: MonkeyPatch,
    options: _HTTPXMockOptions,
    mock: HTTPXMock,
    backend: HttpxBackend,
) -> None:
    # Mock synchronous requests
    real_handle_request = backend.httpx.HTTPTransport.handle_request

    def mocked_handle_request(transport, request):  # type: ignore[no-untyped-def]
        if options.should_mock(request):
            return mock._handle_request(backend, transport, request)
        return real_handle_request(transport, request)

    monkeypatch.setattr(
        backend.httpx.HTTPTransport,
        "handle_request",
        mocked_handle_request,
    )

    # Mock asynchronous requests
    real_handle_async_request = backend.httpx.AsyncHTTPTransport.handle_async_request

    async def mocked_handle_async_request(transport, request):  # type: ignore[no-untyped-def]
        if options.should_mock(request):
            return await mock._handle_async_request(backend, transport, request)
        return await real_handle_async_request(transport, request)

    monkeypatch.setattr(
        backend.httpx.AsyncHTTPTransport,
        "handle_async_request",
        mocked_handle_async_request,
    )


@pytest.fixture
def httpx_mock(
    monkeypatch: MonkeyPatch,
    request: FixtureRequest,
) -> Generator[HTTPXMock, None, None]:
    httpx_mock_markers: dict = {}

    for marker in request.node.iter_markers("httpx_mock"):
        httpx_mock_markers = marker.kwargs | httpx_mock_markers

    __tracebackhide__ = methodcaller("errisinstance", TypeError)
    options = _HTTPXMockOptions(**httpx_mock_markers)

    mock = HTTPXMock(options)

    # Mock sync and async transports of every installed httpx backend.
    for backend in get_backends():
        _mock_backend(monkeypatch, options, mock, backend)

    yield mock
    try:
        mock._assert_options()
    finally:
        mock.reset()


def pytest_configure(config: Config) -> None:
    config.addinivalue_line(
        "markers",
        "httpx_mock(*, assert_all_responses_were_requested=True, assert_all_requests_were_expected=True, can_send_already_matched_responses=False, should_mock=lambda request: True): Configure httpx_mock fixture.",
    )
