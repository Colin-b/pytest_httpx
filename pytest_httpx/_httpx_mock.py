import re
from typing import List, Union, Optional, Callable, Tuple, Pattern, Any, Dict

import httpcore
import httpx

from pytest_httpx._httpx_internals import stream


# Those types are internally defined within httpcore._types
URL = Tuple[bytes, bytes, Optional[int], bytes]
Headers = List[Tuple[bytes, bytes]]
TimeoutDict = Dict[str, Optional[float]]

Response = Tuple[
    bytes, int, bytes, Headers, Union[httpcore.SyncByteStream, httpcore.AsyncByteStream]
]


def to_request(
    method: bytes,
    url: URL,
    headers: Headers = None,
    stream: Union[httpcore.SyncByteStream, httpcore.AsyncByteStream] = None,
) -> httpx.Request:
    scheme, host, port, path = url
    port = f":{port}" if port not in [80, 443, None] else ""
    path = path.decode() if path != b"/" else ""
    if path.startswith("/?"):
        path = path[1:]
    return httpx.Request(
        method=method.decode(),
        url=f"{scheme.decode()}://{host.decode()}{port}{path}",
        headers=headers,
        stream=stream,
    )


class _RequestMatcher:
    def __init__(
        self,
        url: Union[str, Pattern, httpx.URL] = None,
        method: str = None,
        match_headers: dict = None,
        match_content: bytes = None,
    ):
        self.nb_calls = 0
        self.url = url
        self.method = method.upper() if method else method
        self.headers = match_headers
        self.content = match_content

    def match(self, request: httpx.Request) -> bool:
        return (
            self._url_match(request)
            and self._method_match(request)
            and self._headers_match(request)
            and self._content_match(request)
        )

    def _url_match(self, request: httpx.Request) -> bool:
        if not self.url:
            return True

        # re.Pattern was introduced in Python 3.7
        if isinstance(
            self.url, re._pattern_type if hasattr(re, "_pattern_type") else re.Pattern
        ):
            return self.url.match(str(request.url)) is not None

        if isinstance(self.url, httpx.URL):
            return self.url == request.url

        return self.url == str(request.url)

    def _method_match(self, request: httpx.Request) -> bool:
        if not self.method:
            return True

        return request.method == self.method

    def _headers_match(self, request: httpx.Request) -> bool:
        if not self.headers:
            return True

        return all(
            request.headers.get(header_name) == header_value
            for header_name, header_value in self.headers.items()
        )

    def _content_match(self, request: httpx.Request) -> bool:
        if self.content is None:
            return True

        return request.read() == self.content

    def __str__(self) -> str:
        matcher_description = f"Match {self.method or 'all'} requests"
        if self.url:
            matcher_description += f" on {self.url}"
        if self.headers:
            matcher_description += f" with {self.headers} headers"
            if self.content is not None:
                matcher_description += f" and {self.content} body"
        elif self.content is not None:
            matcher_description += f" with {self.content} body"
        return matcher_description


class HTTPXMock:
    def __init__(self):
        self._requests: List[httpx.Request] = []
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
        :param url: Full URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request(s) to match.
        :param match_headers: HTTP headers identifying the request(s) to match. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request(s) to match. Must be bytes.
        """
        response = to_response(
            status_code, http_version, headers, data, files, json, boundary
        )
        self._responses.append((_RequestMatcher(**matchers), response))

    def add_callback(self, callback: Callable, **matchers):
        """
        Mock the action that will take place if a request match.

        :param callback: The callable that will be called upon reception of the matched request.
        It must expect at least 2 parameters:
         * request: The received httpx.Request.
         * timeout: The timeout linked to the request.
        It should return a valid httpcore response tuple, you can use pytest_httpx.to_response function to create one.
        :param url: Full URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request(s) to match.
        :param match_headers: HTTP headers identifying the request(s) to match. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request(s) to match. Must be bytes.
        """
        self._callbacks.append((_RequestMatcher(**matchers), callback))

    def _handle_request(
        self,
        method: bytes,
        url: URL,
        headers: Headers = None,
        stream: Union[httpcore.SyncByteStream, httpcore.AsyncByteStream] = None,
        timeout: TimeoutDict = None,
    ) -> Response:
        request = to_request(method, url, headers, stream)
        self._requests.append(request)

        response = self._get_response(request)
        if response:
            return response

        callback = self._get_callback(request)
        if callback:
            return callback(request=request, timeout=timeout)

        raise httpx.TimeoutException(
            self._explain_that_no_response_was_found(request), request=request
        )

    def _explain_that_no_response_was_found(self, request: httpx.Request) -> str:
        expect_headers = set(
            [
                header
                for matcher, _ in self._responses + self._callbacks
                if matcher.headers
                for header in matcher.headers
            ]
        )
        expect_body = any(
            [
                matcher.content is not None
                for matcher, _ in self._responses + self._callbacks
            ]
        )

        request_description = f"{request.method} request on {request.url}"
        if expect_headers:
            request_description += f" with {dict({name: value for name, value in request.headers.items() if name in expect_headers})} headers"
            if expect_body:
                request_description += f" and {request.read()} body"
        elif expect_body:
            request_description += f" with {request.read()} body"

        matchers_description = "\n".join(
            [str(matcher) for matcher, _ in self._responses + self._callbacks]
        )

        message = f"No response can be found for {request_description}"
        if matchers_description:
            message += f" amongst:\n{matchers_description}"

        return message

    def _get_response(self, request: httpx.Request) -> Optional[Response]:
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
                return response

        # Or the last registered
        matcher.nb_calls += 1
        return response

    def _get_callback(self, request: httpx.Request) -> Optional[Callable]:
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

    def get_requests(self, **matchers) -> List[httpx.Request]:
        """
        Return all requests sent that match (empty list if no requests were matched).

        :param url: Full URL identifying the requests to retrieve.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the requests to retrieve. Must be a upper cased string value.
        :param match_headers: HTTP headers identifying the requests to retrieve. Must be a dictionary.
        :param match_content: Full HTTP body identifying the requests to retrieve. Must be bytes.
        """
        matcher = _RequestMatcher(**matchers)
        return [request for request in self._requests if matcher.match(request)]

    def get_request(self, **matchers) -> Optional[httpx.Request]:
        """
        Return the single request that match (or None).

        :param url: Full URL identifying the request to retrieve.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
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

    def reset(self, assert_all_responses_were_requested: bool):
        not_called = self._reset_responses() + self._reset_callbacks()

        if assert_all_responses_were_requested:
            matchers_description = "\n".join([str(matcher) for matcher in not_called])

            assert (
                not not_called
            ), f"The following responses are mocked but not requested:\n{matchers_description}"

    def _reset_responses(self) -> List[_RequestMatcher]:
        responses_not_called = [
            matcher for matcher, _ in self._responses if not matcher.nb_calls
        ]
        self._responses.clear()
        return responses_not_called

    def _reset_callbacks(self) -> List[_RequestMatcher]:
        callbacks_not_executed = [
            matcher for matcher, _ in self._callbacks if not matcher.nb_calls
        ]
        self._callbacks.clear()
        return callbacks_not_executed


class _PytestSyncTransport(httpcore.SyncHTTPTransport):
    def __init__(self, mock: HTTPXMock):
        self.mock = mock

    def request(
        self, *args, **kwargs
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.SyncByteStream]:
        return self.mock._handle_request(*args, **kwargs)


class _PytestAsyncTransport(httpcore.AsyncHTTPTransport):
    def __init__(self, mock: HTTPXMock):
        self.mock = mock

    async def request(
        self, *args, **kwargs
    ) -> Tuple[bytes, int, bytes, List[Tuple[bytes, bytes]], httpcore.AsyncByteStream]:
        return self.mock._handle_request(*args, **kwargs)


def to_response(
    status_code: int = 200,
    http_version: str = "HTTP/1.1",
    headers: dict = None,
    data=None,
    files=None,
    json: Any = None,
    boundary: bytes = None,
) -> Response:
    """
    Convert to a valid httpcore response.

    :param status_code: HTTP status code of the response. Default to 200 (OK).
    :param http_version: HTTP protocol version of the response. Default to HTTP/1.1
    :param headers: HTTP headers of the response. Default to no headers.
    :param data: HTTP body of the response, can be an iterator to stream content, bytes, str of the full body or
    a dictionary in case of a multipart.
    :param files: Multipart files.
    :param json: HTTP body of the response (if JSON should be used as content type) if data is not provided.
    :param boundary: Multipart boundary if files is provided.
    """
    headers = (
        [(header.encode(), value.encode()) for header, value in headers.items()]
        if headers
        else []
    )
    body = stream(data=data, files=files, json=json, boundary=boundary)
    return http_version.encode(), status_code, b"", headers, body
