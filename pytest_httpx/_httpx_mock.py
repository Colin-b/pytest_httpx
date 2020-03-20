import re
from typing import List, Union, Optional, Callable, Tuple, Pattern, Any

import httpx
import pytest
from httpx import Request, Response, URL
from httpx._content_streams import encode
from httpx._dispatch.base import SyncDispatcher, AsyncDispatcher


class _RequestMatcher:
    def __init__(
        self,
        url: Union[str, Pattern, URL] = None,
        method: str = None,
        match_headers: dict = None,
        match_content: bytes = None,
    ):
        self.nb_calls = 0
        self.url = url
        self.method = method
        self.headers = match_headers
        self.content = match_content

    def match(self, request: Request) -> bool:
        return (
            self._url_match(request)
            and self._method_match(request)
            and self._headers_match(request)
            and self._content_match(request)
        )

    def _url_match(self, request: Request) -> bool:
        if not self.url:
            return True

        # re.Pattern was introduced in Python 3.7
        if isinstance(
            self.url, re._pattern_type if hasattr(re, "_pattern_type") else re.Pattern
        ):
            return self.url.match(str(request.url)) is not None

        if isinstance(self.url, str):
            return URL(self.url) == request.url

        return self.url == request.url

    def _method_match(self, request: Request) -> bool:
        if not self.method:
            return True

        return request.method == self.method.upper()

    def _headers_match(self, request: Request) -> bool:
        if not self.headers:
            return True

        return all(
            request.headers.get(header_name) == header_value
            for header_name, header_value in self.headers.items()
        )

    def _content_match(self, request: Request) -> bool:
        if self.content is None:
            return True

        return request.read() == self.content


class HTTPXMock:
    def __init__(self):
        self._requests: List[Request] = []
        self._responses: List[Tuple[_RequestMatcher, Response]] = []
        self._callbacks: List[Tuple[_RequestMatcher, Callable]] = []

    def add_response(
        self,
        status_code: int = 200,
        http_version: str = "HTTP/1.1",
        headers: dict = None,
        data=None,
        files=None,
        json: Any = None,
        boundary: bytes = None,
        **matchers,
    ):
        """
        Mock the response that will be sent if a request match.

        :param status_code: HTTP status code of the response to send. Default to 200 (OK).
        :param http_version: HTTP protocol version of the response to send. Default to HTTP/1.1
        :param headers: HTTP headers of the response to send. Default to no headers.
        :param data: HTTP body of the response, can be an iterator to stream content, bytes, str of the full body or
        a dictionary in case of a multipart.
        :param files: Multipart files.
        :param json: HTTP body of the response (if JSON should be used as content type) if data is not provided.
        :param boundary: Multipart boundary if files is provided.
        :param url: Full URL identifying the request(s) to match. Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request(s) to match.
        :param match_headers: HTTP headers identifying the request(s) to match. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request(s) to match. Must be bytes.
        """
        response = Response(
            status_code=status_code,
            http_version=http_version,
            headers=list(headers.items()) if headers else [],
            stream=encode(data=data, files=files, json=json, boundary=boundary),
            request=None,  # Will be set upon reception of the actual request
        )
        self._responses.append((_RequestMatcher(**matchers), response))

    def add_callback(self, callback: Callable, **matchers):
        """
        Mock the action that will take place if a request match.

        :param callback: The callable that will be called upon reception of the matched request.
        It must expect at least 2 parameters:
         * request: The received request.
         * timeout: The timeout linked to the request.
        It should return an httpx.Response instance.
        :param url: Full URL identifying the request(s) to match. Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request(s) to match.
        :param match_headers: HTTP headers identifying the request(s) to match. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request(s) to match. Must be bytes.
        """
        self._callbacks.append((_RequestMatcher(**matchers), callback))

    def _handle_request(self, request: Request, *args, **kwargs) -> Response:
        self._requests.append(request)

        response = self._get_response(request)
        if response:
            return response

        callback = self._get_callback(request)
        if callback:
            return callback(request=request, *args, **kwargs)

        raise httpx.HTTPError(
            f"No mock can be found for {request.method} request on {request.url}.",
            request=request,
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

    def get_requests(self, **matchers) -> List[Request]:
        """
        Return all requests sent that match (empty list if no requests were matched).

        :param url: Full URL identifying the requests to retrieve. Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the requests to retrieve. Must be a upper cased string value.
        :param match_headers: HTTP headers identifying the requests to retrieve. Must be a dictionary.
        :param match_content: Full HTTP body identifying the requests to retrieve. Must be bytes.
        """
        matcher = _RequestMatcher(**matchers)
        return [request for request in self._requests if matcher.match(request)]

    def get_request(self, **matchers) -> Optional[Request]:
        """
        Return the single request that match (or None).

        :param url: Full URL identifying the request to retrieve. Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request to retrieve. Must be a upper cased string value.
        :param match_headers: HTTP headers identifying the request to retrieve. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request to retrieve. Must be bytes.
        :raises AssertionError: in case more than one request match.
        """
        requests = self.get_requests(**matchers)
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
        httpx.Client,
        "dispatcher_for_url",
        lambda self, url: _PytestSyncDispatcher(mock),
    )
    # Mock asynchronous requests
    monkeypatch.setattr(
        httpx.AsyncClient,
        "dispatcher_for_url",
        lambda self, url: _PytestAsyncDispatcher(mock),
    )
    yield mock
    mock.assert_and_reset()


# TODO Allow to assert requests content / files / whatever
