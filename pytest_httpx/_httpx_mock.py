from typing import Any
import warnings

import httpx

from pytest_httpx import _httpx_internals


def to_response(
    status_code: int = 200,
    http_version: str = "HTTP/1.1",
    headers: _httpx_internals.HeaderTypes = None,
    data=None,
    files=None,
    json: Any = None,
    boundary: bytes = None,
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
        # TODO Allow to provide content
        content=None,
        # TODO Allow to provide text
        text=None,
        # TODO Allow to provide html
        html=None,
        json=json,
        stream=_httpx_internals.stream(data=data, files=files, boundary=boundary)
        if json is None
        else None,
        extensions={"http_version": http_version.encode("ascii")},
    )
