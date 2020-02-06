import re
from typing import List, Union, Optional, Callable, Tuple, Pattern

import httpx
import pytest
from httpx import Request, Response, Timeout, URL, content_streams
from httpx.dispatch.base import SyncDispatcher, AsyncDispatcher


class _RequestMatcher:
    def __init__(self, url: Union[str, Pattern, URL], method: str):
        # TODO Allow non strict URL params checking
        self.nb_calls = 0
        self.url = url
        self.method = method.upper()

    def match(self, request: Request) -> bool:
        # TODO Allow to match on anything from the request
        return self._url_match(request) and request.method == self.method

    def _url_match(self, request: Request) -> bool:
        # re.Pattern was introduced in Python 3.7
        if isinstance(
            self.url, re._pattern_type if hasattr(re, "_pattern_type") else re.Pattern
        ):
            return self.url.match(str(request.url)) is not None
        if isinstance(self.url, str):
            return URL(self.url) == request.url
        return self.url == request.url


class HTTPXMock:
    def __init__(self):
        self._requests: List[Request] = []
        self._responses: List[Tuple[_RequestMatcher, Response]] = []
        self._callbacks: List[Tuple[_RequestMatcher, Callable]] = []

    def add_response(
        self,
        url: Union[str, Pattern, URL],
        method: str = "GET",
        status_code: int = 200,
        http_version: str = "HTTP/1.1",
        headers: dict = None,
        **content,
    ):
        """
        Mock the response that will be sent if a request is sent to this URL using this method.

        :param url: Full URL identifying the request. Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request. Default to GET.
        :param status_code: HTTP status code of the response to send. Default to 200 (OK).
        :param http_version: HTTP protocol version of the response to send. Default to HTTP/1.1
        :param headers: HTTP headers of the response to send. Default to no headers.
        :param data: HTTP body of the response, can be an iterator to stream content, bytes, str of the full body or
        a dictionary in case of a multipart.
        :param files: Multipart files.
        :param json: HTTP body of the response (if JSON should be used as content type) if data is not provided.
        :param boundary: Multipart boundary if files is provided.
        """
        response = Response(
            status_code=status_code,
            http_version=http_version,
            headers=list(headers.items()) if headers else [],
            stream=content_streams.encode(**content),
            request=None,  # Will be set upon reception of the actual request
        )
        self._responses.append((_RequestMatcher(url, method), response))

    def add_callback(
        self, callback: Callable, url: Union[str, Pattern, URL], method: str = "GET"
    ):
        """
        Mock the action that will take place if a request is sent to this URL using this method.

        :param callback: The callable that will be called upon reception of the request.
        It must expect at least 2 parameters:
         * request: The received request.
         * timeout: The timeout linked to the request.
        It should return an httpx.Response instance.
        :param url: Full URL identifying the request. Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request. Default to GET.
        """
        self._callbacks.append((_RequestMatcher(url, method), callback))

    def _handle_request(
        self, request: Request, timeout: Optional[Timeout], *args, **kwargs
    ) -> Response:
        self._requests.append(request)

        response = self._get_response(request)
        if response:
            return response

        callback = self._get_callback(request)
        if callback:
            return callback(request=request, timeout=timeout, *args, **kwargs)

        raise Exception(
            f"No mock can be found for {request.method} request on {request.url}."
        )

    def _get_response(self, request: Request) -> Optional[Response]:
        responses = [
            (matcher, response)
            for matcher, response in self._responses
            if matcher.match(request)
        ]

        # No response match this request
        if not responses:
            return

        # Responses match this request
        for matcher, response in responses:
            # Return the first not yet called
            if not matcher.nb_calls:
                matcher.nb_calls += 1
                response.request = request
                return response

        # Or the last registered
        matcher.nb_calls += 1
        response.request = request
        return response

    def _get_callback(self, request: Request) -> Optional[Callable]:
        callbacks = [
            (matcher, callback)
            for matcher, callback in self._callbacks
            if matcher.match(request)
        ]

        # No callback match this request
        if not callbacks:
            return

        # Callbacks match this request
        for matcher, callback in callbacks:
            # Return the first not yet called
            if not matcher.nb_calls:
                matcher.nb_calls += 1
                return callback

        # Or the last registered
        matcher.nb_calls += 1
        return callback

    def get_requests(
        self, url: Union[str, Pattern, URL], method: str = "GET"
    ) -> List[Request]:
        """
        Return all requests sent to this URL using this method (empty list if no requests was sent).

        :param url: Full URL identifying the requests. Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the requests. Must be a upper cased string value. Default to GET.
        """
        matcher = _RequestMatcher(url, method)
        return [request for request in self._requests if matcher.match(request)]

    def get_request(
        self, url: Union[str, Pattern, URL], method: str = "GET"
    ) -> Optional[Request]:
        """
        Return the request sent to this URL using this method (or None).

        :param url: Full URL identifying the request. Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request. Must be a upper cased string value. Default to GET.
        """
        requests = self.get_requests(url, method)
        assert (
            len(requests) <= 1
        ), f"More than one request ({len(requests)}) matched, use get_requests instead."
        return requests[0] if requests else None

    def assert_and_reset(self):
        self._assert_responses_sent()
        self._assert_callbacks_executed()

    def _assert_responses_sent(self):
        responses_not_called = [
            response for matcher, response in self._responses if not matcher.nb_calls
        ]
        self._responses.clear()
        assert (
            not responses_not_called
        ), f"The following responses are mocked but not requested: {responses_not_called}"

    def _assert_callbacks_executed(self):
        callbacks_not_executed = [
            callback for matcher, callback in self._callbacks if not matcher.nb_calls
        ]
        self._callbacks.clear()
        assert (
            not callbacks_not_executed
        ), f"The following callbacks are registered but not executed: {callbacks_not_executed}"


class _PytestSyncDispatcher(SyncDispatcher):
    def __init__(self, mock: HTTPXMock):
        self.mock = mock

    def send(self, *args, **kwargs) -> Response:
        return self.mock._handle_request(*args, **kwargs)


class _PytestAsyncDispatcher(AsyncDispatcher):
    def __init__(self, mock: HTTPXMock):
        self.mock = mock

    async def send(self, *args, **kwargs) -> Response:
        return self.mock._handle_request(*args, **kwargs)


@pytest.fixture
def httpx_mock(monkeypatch) -> HTTPXMock:
    mock = HTTPXMock()
    # Mock synchronous requests
    monkeypatch.setattr(
        httpx.client.Client,
        "dispatcher_for_url",
        lambda self, url: _PytestSyncDispatcher(mock),
    )
    # Mock asynchronous requests
    monkeypatch.setattr(
        httpx.client.AsyncClient,
        "dispatcher_for_url",
        lambda self, url: _PytestAsyncDispatcher(mock),
    )
    yield mock
    mock.assert_and_reset()
