import base64
from typing import Union, Optional
from collections.abc import Sequence, Iterable, AsyncIterator, Iterator

from pytest_httpx._httpx_compat import httpx, HttpxBackend, get_backends, httpcore

# Those types are internally defined within httpx._types
HeaderTypes = Union[
    httpx.Headers,
    dict[str, str],
    dict[bytes, bytes],
    Sequence[tuple[str, str]],
    Sequence[tuple[bytes, bytes]],
]
PrimitiveData = Optional[Union[str, int, float, bool]]


def _iterator_stream_bases() -> list[type]:
    bases: list[type] = []

    for backend in get_backends():
        bases.append(backend.httpx.SyncByteStream)
        bases.append(backend.httpx.AsyncByteStream)

    return bases


class IteratorStream(*_iterator_stream_bases()):  # type: ignore[misc]
    def __init__(self, stream: Iterable[bytes]):
        self._stream = stream

    def __iter__(self) -> Iterator[bytes]:
        yield from self._stream

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self._stream:
            yield chunk


def _to_httpx_url(
    backend: HttpxBackend, url: httpcore.URL, headers: list[tuple[bytes, bytes]]
) -> httpx.URL:
    for name, value in headers:
        if b"Proxy-Authorization" == name:
            return backend.httpx.URL(
                scheme=url.scheme.decode(),
                host=url.host.decode(),
                port=url.port,
                raw_path=url.target,
                userinfo=base64.b64decode(value[6:]),
            )

    return backend.httpx.URL(
        scheme=url.scheme.decode(),
        host=url.host.decode(),
        port=url.port,
        raw_path=url.target,
    )


def _proxy_url(
    backend: HttpxBackend,
    real_transport: Union[httpx.HTTPTransport, httpx.AsyncHTTPTransport],
) -> Optional[httpx.URL]:
    if isinstance(
        real_pool := real_transport._pool,
        (backend.httpcore.HTTPProxy, backend.httpcore.AsyncHTTPProxy),
    ):
        return _to_httpx_url(backend, real_pool._proxy_url, real_pool._proxy_headers)
    return None
