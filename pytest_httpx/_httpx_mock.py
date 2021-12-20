import re
from typing import List, Union, Optional, Callable, Tuple, Pattern, Any, Dict
from urllib.parse import parse_qs
import warnings

import httpx

from pytest_httpx import _httpx_internals

# re.Pattern was introduced in Python 3.7
pattern_type = re._pattern_type if hasattr(re, "_pattern_type") else re.Pattern


class _RequestMatcher:
    def __init__(
        self,
        url: Optional[Union[str, Pattern[str], httpx.URL]] = None,
        method: Optional[str] = None,
        match_headers: Optional[Dict[str, Any]] = None,
        match_content: Optional[bytes] = None,
    ):
        self.nb_calls = 0
        self.url = httpx.URL(url) if url and isinstance(url, str) else url
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

        if isinstance(self.url, pattern_type):
            return self.url.match(str(request.url)) is not None

        # Compare query parameters apart as order of parameters should not matter
        request_qs = parse_qs(request.url.query)
        qs = parse_qs(self.url.query)

        # Remove the query parameters from the original URL to compare everything besides query parameters
        request_url = request.url.copy_with(query=None)
        url = self.url.copy_with(query=None)

        return (request_qs == qs) and (url == request_url)

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
    def __init__(self) -> None:
        self._requests: List[httpx.Request] = []
        self._responses: List[Tuple[_RequestMatcher, httpx.Response]] = []
        self._callbacks: List[
            Tuple[
                _RequestMatcher,
                Callable[[httpx.Request], httpx.Response],
            ]
        ] = []

    def add_response(
        self,
        status_code: int = 200,
        http_version: str = "HTTP/1.1",
        headers: _httpx_internals.HeaderTypes = None,
        content: Optional[bytes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        stream: Any = None,
        data: Any = None,
        files: Any = None,
        json: Any = None,
        boundary: bytes = None,
        **matchers,
    ) -> None:
        """
        Mock the response that will be sent if a request match.

        :param status_code: HTTP status code of the response to send. Default to 200 (OK).
        :param http_version: HTTP protocol version of the response to send. Default to HTTP/1.1
        :param headers: HTTP headers of the response to send. Default to no headers.
        :param content: HTTP body of the response (as bytes).
        :param text: HTTP body of the response (as string).
        :param html: HTTP body of the response (as HTML string content).
        :param stream: HTTP body of the response (as httpx.SyncByteStream or httpx.AsyncByteStream) as stream content.
        :param data: HTTP body of the response as a dictionary in case of a multipart.
        :param files: Multipart files.
        :param json: HTTP body of the response (if JSON should be used as content type) if data is not provided.
        :param boundary: Multipart boundary if files is provided.
        :param url: Full URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request(s) to match.
        :param match_headers: HTTP headers identifying the request(s) to match. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request(s) to match. Must be bytes.
        """
        stream_data_provided = (
            (json is None)
            and (content is None)
            and (text is None)
            and (html is None)
            and (stream is None)
        )
        response = httpx.Response(
            status_code=status_code,
            extensions={"http_version": http_version.encode("ascii")},
            headers=headers,
            json=json,
            content=content,
            text=text,
            html=html,
            stream=_httpx_internals.stream(data=data, files=files, boundary=boundary)
            if stream_data_provided
            else stream,
        )
        self._responses.append((_RequestMatcher(**matchers), response))

    def add_callback(
        self, callback: Callable[[httpx.Request], httpx.Response], **matchers
    ) -> None:
        """
        Mock the action that will take place if a request match.

        :param callback: The callable that will be called upon reception of the matched request.
        It must expect one parameter, the received httpx.Request and should return a httpx.Response.
        :param url: Full URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request(s) to match.
        :param match_headers: HTTP headers identifying the request(s) to match. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request(s) to match. Must be bytes.
        """
        self._callbacks.append((_RequestMatcher(**matchers), callback))

    def _handle_request(
        self,
        request: httpx.Request,
    ) -> httpx.Response:
        self._requests.append(request)

        response = self._get_response(request)
        if response:
            return response

        callback = self._get_callback(request)
        if callback:
            return callback(request)

        raise httpx.TimeoutException(
            self._explain_that_no_response_was_found(request), request=request
        )

    def _explain_that_no_response_was_found(self, request: httpx.Request) -> str:
        matchers = [matcher for matcher, _ in self._responses + self._callbacks]
        expect_headers = set(
            [
                header
                for matcher in matchers
                if matcher.headers
                for header in matcher.headers
            ]
        )
        expect_body = any([matcher.content is not None for matcher in matchers])

        request_description = f"{request.method} request on {request.url}"
        if expect_headers:
            request_description += f" with {dict({name: value for name, value in request.headers.items() if name in expect_headers})} headers"
            if expect_body:
                request_description += f" and {request.read()} body"
        elif expect_body:
            request_description += f" with {request.read()} body"

        matchers_description = "\n".join([str(matcher) for matcher in matchers])

        message = f"No response can be found for {request_description}"
        if matchers_description:
            message += f" amongst:\n{matchers_description}"

        return message

    def _get_response(self, request: httpx.Request) -> Optional[httpx.Response]:
        responses = [
            (matcher, response)
            for matcher, response in self._responses
            if matcher.match(request)
        ]

        # No response match this request
        if not responses:
            return None

        # Responses match this request
        for matcher, response in responses:
            # Return the first not yet called
            if not matcher.nb_calls:
                matcher.nb_calls += 1
                return response

        # Or the last registered
        matcher.nb_calls += 1
        return response

    def _get_callback(
        self, request: httpx.Request
    ) -> Optional[Callable[[httpx.Request], httpx.Response]]:
        callbacks = [
            (matcher, callback)
            for matcher, callback in self._callbacks
            if matcher.match(request)
        ]

        # No callback match this request
        if not callbacks:
            return None

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

    def reset(self, assert_all_responses_were_requested: bool) -> None:
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


class _PytestSyncTransport(httpx.BaseTransport):
    def __init__(self, mock: HTTPXMock):
        self.mock = mock

    def handle_request(self, *args, **kwargs) -> httpx.Response:
        return self.mock._handle_request(*args, **kwargs)


class _PytestAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(self, mock: HTTPXMock):
        self.mock = mock

    async def handle_async_request(self, *args, **kwargs) -> httpx.Response:
        return self.mock._handle_request(*args, **kwargs)


def to_response(
    status_code: int = 200,
    http_version: str = "HTTP/1.1",
    headers: _httpx_internals.HeaderTypes = None,
    data=None,
    files=None,
    json: Any = None,
    boundary: Optional[bytes] = None,
) -> httpx.Response:
    """
    Convert to a valid httpx response.

    :param status_code: HTTP status code of the response. Default to 200 (OK).
    :param http_version: HTTP protocol version of the response. Default to HTTP/1.1
    :param headers: HTTP headers of the response. Default to no headers.
    :param data: HTTP body of the response, can be an iterator to stream content, bytes, str of the full body or
    a dictionary in case of a multipart.
    :param files: Multipart files.
    :param json: HTTP body of the response (if JSON should be used as content type) if data is not provided.
    :param boundary: Multipart boundary if files is provided.
    """
    warnings.warn(
        "pytest_httpx.to_response will be removed in a future version. Use httpx.Response instead.",
        DeprecationWarning,
    )
    return httpx.Response(
        status_code=status_code,
        headers=headers,
        json=json,
        stream=_httpx_internals.stream(data=data, files=files, boundary=boundary)
        if json is None
        else None,
        extensions={"http_version": http_version.encode("ascii")},
    )
