import base64
import copy
import inspect
import json
import re
from typing import List, Union, Optional, Callable, Tuple, Pattern, Any, Dict, Awaitable

import httpcore
import httpx

from pytest_httpx import _httpx_internals


def _to_httpx_url(url: httpcore.URL, headers: list[tuple[bytes, bytes]]) -> httpx.URL:
    for name, value in headers:
        if b"Proxy-Authorization" == name:
            return httpx.URL(
                scheme=url.scheme.decode(),
                host=url.host.decode(),
                port=url.port,
                raw_path=url.target,
                userinfo=base64.b64decode(value[6:]),
            )

    return httpx.URL(
        scheme=url.scheme.decode(),
        host=url.host.decode(),
        port=url.port,
        raw_path=url.target,
    )


def _url_match(
    url_to_match: Union[Pattern[str], httpx.URL], received: httpx.URL
) -> bool:
    if isinstance(url_to_match, re.Pattern):
        return url_to_match.match(str(received)) is not None

    # Compare query parameters apart as order of parameters should not matter
    received_params = dict(received.params)
    params = dict(url_to_match.params)

    # Remove the query parameters from the original URL to compare everything besides query parameters
    received_url = received.copy_with(query=None)
    url = url_to_match.copy_with(query=None)

    return (received_params == params) and (url == received_url)


def _request_description(
    real_transport: Union[httpx.BaseTransport, httpx.AsyncBaseTransport],
    request: httpx.Request,
    expected_headers: set[bytes],
    expect_body: bool,
    expect_proxy: bool,
) -> str:
    request_description = f"{request.method} request on {request.url}"
    if extra_description := extra_request_description(
        real_transport, request, expected_headers, expect_body, expect_proxy
    ):
        request_description += f" with {extra_description}"
    return request_description


def _proxy_url(
    real_transport: Union[httpx.BaseTransport, httpx.AsyncBaseTransport]
) -> Optional[httpx.URL]:
    if isinstance(real_transport, httpx.HTTPTransport):
        if isinstance(real_pool := real_transport._pool, httpcore.HTTPProxy):
            return _to_httpx_url(real_pool._proxy_url, real_pool._proxy_headers)

    if isinstance(real_transport, httpx.AsyncHTTPTransport):
        if isinstance(real_pool := real_transport._pool, httpcore.AsyncHTTPProxy):
            return _to_httpx_url(real_pool._proxy_url, real_pool._proxy_headers)


def extra_request_description(
    real_transport: Union[httpx.BaseTransport, httpx.AsyncBaseTransport],
    request: httpx.Request,
    expected_headers: set[bytes],
    expect_body: bool,
    expect_proxy: bool,
):
    extra_description = []

    if expected_headers:
        headers_encoding = request.headers.encoding
        present_headers = {}
        # Can be cleaned based on the outcome of https://github.com/encode/httpx/discussions/2841
        for name, lower_name, value in request.headers._list:
            if lower_name in expected_headers:
                name = name.decode(headers_encoding)
                if name in present_headers:
                    present_headers[name] += f", {value.decode(headers_encoding)}"
                else:
                    present_headers[name] = value.decode(headers_encoding)

        extra_description.append(f"{present_headers} headers")

    if expect_body:
        extra_description.append(f"{request.read()} body")

    if expect_proxy:
        extra_description.append(f"{_proxy_url(real_transport)} proxy URL")

    return " and ".join(extra_description)


class _RequestMatcher:
    def __init__(
        self,
        url: Optional[Union[str, Pattern[str], httpx.URL]] = None,
        method: Optional[str] = None,
        proxy_url: Optional[Union[str, Pattern[str], httpx.URL]] = None,
        match_headers: Optional[Dict[str, Any]] = None,
        match_content: Optional[bytes] = None,
        match_json: Optional[Any] = None,
    ):
        self.nb_calls = 0
        self.url = httpx.URL(url) if url and isinstance(url, str) else url
        self.method = method.upper() if method else method
        self.headers = match_headers
        if match_content is not None and match_json is not None:
            raise ValueError(
                "Only one way of matching against the body can be provided. If you want to match against the JSON decoded representation, use match_json. Otherwise, use match_content."
            )
        self.content = match_content
        self.json = match_json
        self.proxy_url = (
            httpx.URL(proxy_url)
            if proxy_url and isinstance(proxy_url, str)
            else proxy_url
        )

    def match(
        self,
        real_transport: Union[httpx.BaseTransport, httpx.AsyncBaseTransport],
        request: httpx.Request,
    ) -> bool:
        return (
            self._url_match(request)
            and self._method_match(request)
            and self._headers_match(request)
            and self._content_match(request)
            and self._proxy_match(real_transport)
        )

    def _url_match(self, request: httpx.Request) -> bool:
        if not self.url:
            return True

        return _url_match(self.url, request.url)

    def _method_match(self, request: httpx.Request) -> bool:
        if not self.method:
            return True

        return request.method == self.method

    def _headers_match(self, request: httpx.Request) -> bool:
        if not self.headers:
            return True

        encoding = request.headers.encoding
        request_headers = {}
        # Can be cleaned based on the outcome of https://github.com/encode/httpx/discussions/2841
        for raw_name, raw_value in request.headers.raw:
            if raw_name in request_headers:
                request_headers[raw_name] += b", " + raw_value
            else:
                request_headers[raw_name] = raw_value

        return all(
            request_headers.get(header_name.encode(encoding))
            == header_value.encode(encoding)
            for header_name, header_value in self.headers.items()
        )

    def _content_match(self, request: httpx.Request) -> bool:
        if self.content is None and self.json is None:
            return True
        if self.content is not None:
            return request.read() == self.content
        try:
            # httpx._content.encode_json hard codes utf-8 encoding.
            return json.loads(request.read().decode("utf-8")) == self.json
        except json.decoder.JSONDecodeError:
            return False

    def _proxy_match(
        self, real_transport: Union[httpx.BaseTransport, httpx.AsyncBaseTransport]
    ) -> bool:
        if not self.proxy_url:
            return True

        if real_proxy_url := _proxy_url(real_transport):
            return _url_match(self.proxy_url, real_proxy_url)

        return False

    def __str__(self) -> str:
        matcher_description = f"Match {self.method or 'all'} requests"
        if self.url:
            matcher_description += f" on {self.url}"
        if extra_description := self._extra_description():
            matcher_description += f" with {extra_description}"
        return matcher_description

    def _extra_description(self) -> str:
        extra_description = []

        if self.headers:
            extra_description.append(f"{self.headers} headers")
        if self.content is not None:
            extra_description.append(f"{self.content} body")
        if self.json is not None:
            extra_description.append(f"{self.json} json body")
        if self.proxy_url:
            extra_description.append(f"{self.proxy_url} proxy URL")

        return " and ".join(extra_description)


class HTTPXMock:
    def __init__(self) -> None:
        self._requests: List[
            Tuple[Union[httpx.BaseTransport, httpx.AsyncBaseTransport], httpx.Request]
        ] = []
        self._callbacks: List[
            Tuple[
                _RequestMatcher,
                Callable[
                    [httpx.Request],
                    Union[
                        Optional[httpx.Response], Awaitable[Optional[httpx.Response]]
                    ],
                ],
            ]
        ] = []

    def add_response(
        self,
        status_code: int = 200,
        http_version: str = "HTTP/1.1",
        headers: Optional[_httpx_internals.HeaderTypes] = None,
        content: Optional[bytes] = None,
        text: Optional[str] = None,
        html: Optional[str] = None,
        stream: Any = None,
        json: Any = None,
        **matchers: Any,
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
        :param json: HTTP body of the response (if JSON should be used as content type) if data is not provided.
        :param url: Full URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request(s) to match.
        :param proxy_url: Full proxy URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param match_headers: HTTP headers identifying the request(s) to match. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request(s) to match. Must be bytes.
        :param match_json: JSON decoded HTTP body identifying the request(s) to match. Must be JSON encodable.
        """

        json = copy.deepcopy(json) if json is not None else None

        def response_callback(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=status_code,
                extensions={"http_version": http_version.encode("ascii")},
                headers=headers,
                json=json,
                content=content,
                text=text,
                html=html,
                stream=stream,
            )

        self.add_callback(response_callback, **matchers)

    def add_callback(
        self,
        callback: Callable[
            [httpx.Request],
            Union[Optional[httpx.Response], Awaitable[Optional[httpx.Response]]],
        ],
        **matchers: Any,
    ) -> None:
        """
        Mock the action that will take place if a request match.

        :param callback: The callable that will be called upon reception of the matched request.
        It must expect one parameter, the received httpx.Request and should return a httpx.Response.
        :param url: Full URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request(s) to match.
        :param proxy_url: Full proxy URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param match_headers: HTTP headers identifying the request(s) to match. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request(s) to match. Must be bytes.
        :param match_json: JSON decoded HTTP body identifying the request(s) to match. Must be JSON encodable.
        """
        self._callbacks.append((_RequestMatcher(**matchers), callback))

    def add_exception(self, exception: Exception, **matchers: Any) -> None:
        """
        Raise an exception if a request match.

        :param exception: The exception that will be raised upon reception of the matched request.
        :param url: Full URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request(s) to match.
        :param proxy_url: Full proxy URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param match_headers: HTTP headers identifying the request(s) to match. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request(s) to match. Must be bytes.
        :param match_json: JSON decoded HTTP body identifying the request(s) to match. Must be JSON encodable.
        """

        def exception_callback(request: httpx.Request) -> None:
            if isinstance(exception, httpx.RequestError):
                exception.request = request
            raise exception

        self.add_callback(exception_callback, **matchers)

    def _handle_request(
        self,
        real_transport: httpx.BaseTransport,
        request: httpx.Request,
    ) -> httpx.Response:
        self._requests.append((real_transport, request))

        callback = self._get_callback(real_transport, request)
        if callback:
            response = callback(request)

            if response:
                return _unread(response)

        raise httpx.TimeoutException(
            self._explain_that_no_response_was_found(real_transport, request),
            request=request,
        )

    async def _handle_async_request(
        self,
        real_transport: httpx.AsyncBaseTransport,
        request: httpx.Request,
    ) -> httpx.Response:
        self._requests.append((real_transport, request))

        callback = self._get_callback(real_transport, request)
        if callback:
            response = callback(request)

            if response:
                if inspect.isawaitable(response):
                    response = await response
                return _unread(response)

        raise httpx.TimeoutException(
            self._explain_that_no_response_was_found(real_transport, request),
            request=request,
        )

    def _explain_that_no_response_was_found(
        self,
        real_transport: Union[httpx.BaseTransport, httpx.AsyncBaseTransport],
        request: httpx.Request,
    ) -> str:
        matchers = [matcher for matcher, _ in self._callbacks]
        headers_encoding = request.headers.encoding
        expected_headers = set(
            [
                # httpx uses lower cased header names as internal key
                header.lower().encode(headers_encoding)
                for matcher in matchers
                if matcher.headers
                for header in matcher.headers
            ]
        )
        expect_body = any(
            [
                matcher.content is not None or matcher.json is not None
                for matcher in matchers
            ]
        )
        expect_proxy = any([matcher.proxy_url is not None for matcher in matchers])

        request_description = _request_description(
            real_transport, request, expected_headers, expect_body, expect_proxy
        )

        matchers_description = "\n".join([str(matcher) for matcher in matchers])

        message = f"No response can be found for {request_description}"
        if matchers_description:
            message += f" amongst:\n{matchers_description}"

        return message

    def _get_callback(
        self,
        real_transport: Union[httpx.BaseTransport, httpx.AsyncBaseTransport],
        request: httpx.Request,
    ) -> Optional[
        Callable[
            [httpx.Request],
            Union[Optional[httpx.Response], Awaitable[Optional[httpx.Response]]],
        ]
    ]:
        callbacks = [
            (matcher, callback)
            for matcher, callback in self._callbacks
            if matcher.match(real_transport, request)
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

    def get_requests(self, **matchers: Any) -> List[httpx.Request]:
        """
        Return all requests sent that match (empty list if no requests were matched).

        :param url: Full URL identifying the requests to retrieve.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the requests to retrieve. Must be an upper-cased string value.
        :param proxy_url: Full proxy URL identifying the requests to retrieve.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param match_headers: HTTP headers identifying the requests to retrieve. Must be a dictionary.
        :param match_content: Full HTTP body identifying the requests to retrieve. Must be bytes.
        :param match_json: JSON decoded HTTP body identifying the requests to retrieve. Must be JSON encodable.
        """
        matcher = _RequestMatcher(**matchers)
        return [
            request
            for real_transport, request in self._requests
            if matcher.match(real_transport, request)
        ]

    def get_request(self, **matchers: Any) -> Optional[httpx.Request]:
        """
        Return the single request that match (or None).

        :param url: Full URL identifying the request to retrieve.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request to retrieve. Must be an upper-cased string value.
        :param proxy_url: Full proxy URL identifying the request to retrieve.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param match_headers: HTTP headers identifying the request to retrieve. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request to retrieve. Must be bytes.
        :param match_json: JSON decoded HTTP body identifying the request to retrieve. Must be JSON encodable.
        :raises AssertionError: in case more than one request match.
        """
        requests = self.get_requests(**matchers)
        assert (
            len(requests) <= 1
        ), f"More than one request ({len(requests)}) matched, use get_requests instead."
        return requests[0] if requests else None

    def reset(self, assert_all_responses_were_requested: bool) -> None:
        self._requests.clear()
        not_called = self._reset_callbacks()

        if assert_all_responses_were_requested:
            matchers_description = "\n".join([str(matcher) for matcher in not_called])

            assert (
                not not_called
            ), f"The following responses are mocked but not requested:\n{matchers_description}"

    def _reset_callbacks(self) -> List[_RequestMatcher]:
        callbacks_not_executed = [
            matcher for matcher, _ in self._callbacks if not matcher.nb_calls
        ]
        self._callbacks.clear()
        return callbacks_not_executed


class _PytestSyncTransport(httpx.BaseTransport):
    def __init__(self, real_transport: httpx.BaseTransport, mock: HTTPXMock):
        self._real_transport = real_transport
        self._mock = mock

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._mock._handle_request(self._real_transport, request)


class _PytestAsyncTransport(httpx.AsyncBaseTransport):
    def __init__(self, real_transport: httpx.AsyncBaseTransport, mock: HTTPXMock):
        self._real_transport = real_transport
        self._mock = mock

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await self._mock._handle_async_request(self._real_transport, request)


def _unread(response: httpx.Response) -> httpx.Response:
    # Allow to read the response on client side
    response.is_stream_consumed = False
    response.is_closed = False
    if hasattr(response, "_content"):
        del response._content
    return response
