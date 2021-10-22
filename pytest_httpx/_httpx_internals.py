from typing import Union, Dict, Sequence, Tuple, Iterable
import warnings

import httpx

# TODO Get rid of this internal import
from httpx._content import IteratorByteStream, AsyncIteratorByteStream

# Those types are internally defined within httpx._types
HeaderTypes = Union[
    "Headers",
    Dict[str, str],
    Dict[bytes, bytes],
    Sequence[Tuple[str, str]],
    Sequence[Tuple[bytes, bytes]],
]


class IteratorStream(AsyncIteratorByteStream, IteratorByteStream):
    def __init__(self, stream: Iterable):
        class Stream:
            def __iter__(self):
                for chunk in stream:
                    yield chunk

            async def __aiter__(self):
                for chunk in stream:
                    yield chunk

        AsyncIteratorByteStream.__init__(self, stream=Stream())
        IteratorByteStream.__init__(self, stream=Stream())


def stream(
    data, files, boundary: bytes
) -> Union[httpx.AsyncByteStream, httpx.SyncByteStream]:
    if files:
        # TODO Get rid of this internal import
        # import is performed at runtime when needed to reduce impact of internal changes in httpx
        from httpx._multipart import MultipartStream

        return MultipartStream(data=data or {}, files=files, boundary=boundary)

    if isinstance(data, str):
        warnings.warn(
            "data parameter as str will be removed in a future version. Use text parameter instead.",
            DeprecationWarning,
        )
        data = data.encode("utf-8")
    elif data is None:
        data = b""
    elif isinstance(data, bytes):
        warnings.warn(
            "data parameter as bytes will be removed in a future version. Use content parameter instead.",
            DeprecationWarning,
        )

    if isinstance(data, bytes):
        return httpx.ByteStream(data)

    warnings.warn(
        "data parameter as iterator will be removed in a future version. Use stream parameter instead.",
        DeprecationWarning,
    )
    return IteratorStream(data)
