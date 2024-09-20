import copy
import inspect
from operator import methodcaller
from typing import Union, Optional, Callable, Any, NoReturn
from collections.abc import Awaitable

import httpx
from pytest import Mark

from pytest_httpx import _httpx_internals
from pytest_httpx._pretty_print import RequestDescription
from pytest_httpx._request_matcher import _RequestMatcher


class HTTPXMockOptions:
    def __init__(
        self,
        *,
        assert_all_responses_were_requested: bool = True,
        assert_all_requests_were_expected: bool = True,
        non_mocked_hosts: Optional[list[str]] = None,
    ) -> None:
        self.assert_all_responses_were_requested = assert_all_responses_were_requested
        self.assert_all_requests_were_expected = assert_all_requests_were_expected

        if non_mocked_hosts is None:
            non_mocked_hosts = []

        # Ensure redirections to www hosts are handled transparently.
        missing_www = [
            f"www.{host}" for host in non_mocked_hosts if not host.startswith("www.")
        ]
        self.non_mocked_hosts = [*non_mocked_hosts, *missing_www]

    @classmethod
    def from_marker(cls, marker: Mark) -> "HTTPXMockOptions":
        """Initialise from a marker so that the marker kwargs raise an error if incorrect."""
        __tracebackhide__ = methodcaller("errisinstance", TypeError)
        return cls(**marker.kwargs)


class HTTPXMock:
    def __init__(self) -> None:
        self._requests: list[
            tuple[Union[httpx.HTTPTransport, httpx.AsyncHTTPTransport], httpx.Request]
        ] = []
        self._callbacks: list[
            tuple[
                _RequestMatcher,
                Callable[
                    [httpx.Request],
                    Union[
                        Optional[httpx.Response], Awaitable[Optional[httpx.Response]]
                    ],
                ],
            ]
        ] = []
        self._requests_not_matched: list[httpx.Request] = []

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
        real_transport: httpx.HTTPTransport,
        request: httpx.Request,
    ) -> httpx.Response:
        self._requests.append((real_transport, request))

        callback = self._get_callback(real_transport, request)
        if callback:
            response = callback(request)

            if response:
                return _unread(response)

        self._request_not_matched(real_transport, request)

    async def _handle_async_request(
        self,
        real_transport: httpx.AsyncHTTPTransport,
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

        self._request_not_matched(real_transport, request)

    def _request_not_matched(
        self,
        real_transport: Union[httpx.AsyncHTTPTransport, httpx.HTTPTransport],
        request: httpx.Request,
    ) -> NoReturn:
        self._requests_not_matched.append(request)
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

        message = f"No response can be found for {RequestDescription(real_transport, request, matchers)}"

        matchers_description = "\n".join([str(matcher) for matcher in matchers])
        if matchers_description:
            message += f" amongst:\n{matchers_description}"

        return message

    def _get_callback(
        self,
        real_transport: Union[httpx.HTTPTransport, httpx.AsyncHTTPTransport],
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

    def get_requests(self, **matchers: Any) -> list[httpx.Request]:
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

    def reset(self) -> None:
        self._requests.clear()
        self._callbacks.clear()
        self._requests_not_matched.clear()

    def _assert_options(self, options: HTTPXMockOptions) -> None:
        if options.assert_all_responses_were_requested:
            callbacks_not_executed = [
                matcher for matcher, _ in self._callbacks if not matcher.nb_calls
            ]
            matchers_description = "\n".join(
                [str(matcher) for matcher in callbacks_not_executed]
            )

            assert (
                not callbacks_not_executed
            ), f"The following responses are mocked but not requested:\n{matchers_description}"

        if options.assert_all_requests_were_expected:
            assert (
                not self._requests_not_matched
            ), f"The following requests were not expected:\n{self._requests_not_matched}"


def _unread(response: httpx.Response) -> httpx.Response:
    # Allow to read the response on client side
    response.is_stream_consumed = False
    response.is_closed = False
    if hasattr(response, "_content"):
        del response._content
    return response
