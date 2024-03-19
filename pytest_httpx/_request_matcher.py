import json
import re
from typing import Optional, Union, Any
from re import Pattern

import httpx

from pytest_httpx._httpx_internals import _proxy_url


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


class _RequestMatcher:
    def __init__(
        self,
        url: Optional[Union[str, Pattern[str], httpx.URL]] = None,
        method: Optional[str] = None,
        proxy_url: Optional[Union[str, Pattern[str], httpx.URL]] = None,
        match_headers: Optional[dict[str, Any]] = None,
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
        real_transport: Union[httpx.HTTPTransport, httpx.AsyncHTTPTransport],
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
        self, real_transport: Union[httpx.HTTPTransport, httpx.AsyncHTTPTransport]
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
