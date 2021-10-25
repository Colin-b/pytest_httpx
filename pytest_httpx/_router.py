import re
from contextlib import contextmanager
from typing import List, Union, Optional, Callable, Pattern, Any, Generator

import httpx
from respx import patterns as p, MockRouter, Route
from respx.models import AllCalledAssertionError, AllMockedAssertionError, ResolvedRoute

from pytest_httpx import _httpx_internals


class HTTPXMock(MockRouter):
    def add_response(
        self,
        status_code: int = 200,
        http_version: str = "HTTP/1.1",
        headers: _httpx_internals.HeaderTypes = None,
        content=None,
        text=None,
        html=None,
        stream=None,
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
        patterns = self._matchers_to_patterns(**matchers)
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
        return self.route(*patterns).mock(return_value=response)

    def add_callback(self, callback: Callable, **matchers) -> Route:
        """
        Mock the action that will take place if a request match.

        :param callback: The callable that will be called upon reception of the matched request.
        It must expect at least 2 parameters:
         * request: The received httpx.Request.
         * ext: The extensions linked to the request (such as timeout).
        It should return a valid httpcore response tuple, you can use pytest_httpx.to_response function to create one.
        :param url: Full URL identifying the request(s) to match.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the request(s) to match.
        :param match_headers: HTTP headers identifying the request(s) to match. Must be a dictionary.
        :param match_content: Full HTTP body identifying the request(s) to match. Must be bytes.
        """
        patterns = self._matchers_to_patterns(**matchers)
        side_effect = lambda request: callback(request, request.extensions)
        return self.route(*patterns).mock(side_effect=side_effect)

    def get_requests(self, **matchers) -> List[httpx.Request]:
        """
        Return all requests sent that match (empty list if no requests were matched).

        :param url: Full URL identifying the requests to retrieve.
        Can be a str, a re.Pattern instance or a httpx.URL instance.
        :param method: HTTP method identifying the requests to retrieve. Must be a upper cased string value.
        :param match_headers: HTTP headers identifying the requests to retrieve. Must be a dictionary.
        :param match_content: Full HTTP body identifying the requests to retrieve. Must be bytes.
        """
        patterns = self._matchers_to_patterns(**matchers)
        pattern = p.combine(patterns)
        return [
            request
            for request, response in self.calls
            if response and (not pattern or pattern.match(request))
        ]

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

    def reset(self, assert_all_responses_were_requested: bool = False) -> None:
        # Overload super to also clear added routes
        if assert_all_responses_were_requested:
            self.assert_all_called()  # pragma: nocover
        super().reset()
        self.clear()

    @contextmanager
    def resolver(self, request: httpx.Request) -> Generator[ResolvedRoute, None, None]:
        # Overload super to please pytest_httpx's TimeoutException for non-mocked routes
        try:
            with super().resolver(request) as resolved:
                yield resolved
        except AllMockedAssertionError as e:
            raise httpx.TimeoutException(
                self._explain_that_no_response_was_found(request), request=request
            ) from e

    def assert_all_called(self) -> None:
        # Overload super to please pytest_httpx's assertion output for non-called routes
        try:
            super().assert_all_called()
        except AllCalledAssertionError as e:
            non_called_routes = "\n".join(
                (
                    self._explain_route(route)
                    for route in self.routes
                    if not route.called
                )
            )
            raise AllCalledAssertionError(
                f"The following responses are mocked but not requested:\n"
                f"{non_called_routes}"
            ) from e

    def _matchers_to_patterns(
        self,
        url: Union[str, Pattern, httpx.URL] = None,
        method: str = None,
        match_headers: dict = None,
        match_content: bytes = None,
    ) -> List[p.Pattern]:
        patterns = []

        if url:
            if isinstance(
                url,
                re._pattern_type if hasattr(re, "_pattern_type") else re.Pattern,
            ):
                patterns.append(p.URL(url, p.Lookup.REGEX))
            else:
                patterns.append(p.M(url=url))

        if method:
            patterns.append(p.Method(method))

        if match_headers:
            patterns.append(p.Headers(match_headers))

        if match_content:
            patterns.append(p.Content(match_content))

        return patterns

    def _explain_that_no_response_was_found(self, request: httpx.Request) -> str:
        expect_headers = set(
            header
            for headers in filter(
                lambda pat: isinstance(pat, p.Headers),
                (pattern for route in self.routes for pattern in route.pattern),
            )
            for header in headers.value
        )
        expect_body = any(
            filter(
                lambda pat: isinstance(pat, p.Content),
                (pattern for route in self.routes for pattern in route.pattern),
            )
        )

        # NOTE: Only stripping lonely / to not affect assert output
        request_url = (
            str(request.url)
            if request.url.path != "/"
            else str(request.url.copy_with(path=""))
        )

        request_description = f"{request.method} request on {request_url}"
        if expect_headers:
            expected_request_headers = {
                name: value
                for name, value in request.headers.items()
                if name in expect_headers
            }
            request_description += f" with {expected_request_headers} headers"
            if expect_body:
                request_description += f" and {request.read()} body"
        elif expect_body:
            request_description += f" with {request.read()} body"

        matchers_description = "\n".join(
            [self._explain_route(route) for route in self.routes]
        )

        message = f"No response can be found for {request_description}"
        if matchers_description:
            message += f" amongst:\n{matchers_description}"

        return message

    def _explain_route(self, route) -> str:
        # Render a route pattern in a pytest_httpx format
        patterns = list(route.pattern) if route.pattern else []

        find_pattern = lambda pt, ps: next((_ for _ in ps if isinstance(_, pt)), None)
        method = find_pattern(p.Method, patterns)
        headers = find_pattern(p.Headers, patterns)
        content = find_pattern(p.Content, patterns)
        scheme = find_pattern(p.Scheme, patterns)
        host = find_pattern(p.Host, patterns)
        path = find_pattern(p.Path, patterns)
        params = find_pattern(p.Params, patterns)

        matcher_description = f"Match {method.value if method else 'all'} requests"
        if scheme or host or path:
            matcher_description += (
                f" on {scheme.value + '://' if scheme else ''}"
                f"{host.value if host else ''}"
                f"{path.value if path and path != '/' else ''}"
                f"{'?' + str(params.value) if params else ''}"
            )
        if headers:
            matcher_description += f" with {dict(headers.value.items())} headers"
            if content is not None:
                matcher_description += f" and {content.value} body"
        elif content is not None:
            matcher_description += f" with {content.value} body"
        return matcher_description
