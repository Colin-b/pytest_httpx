from typing import (
    Union,
    Dict,
    Sequence,
    Tuple,
    Iterable,
    Optional,
    AsyncIterator,
    Iterator,
    Any,
)
import warnings

import httpx

# TODO Get rid of this internal import
from httpx._content import IteratorByteStream, AsyncIteratorByteStream

# Those types are internally defined within httpx._types
HeaderTypes = Union[
    httpx.Headers,
    Dict[str, str],
    Dict[bytes, bytes],
    Sequence[Tuple[str, str]],
    Sequence[Tuple[bytes, bytes]],
]


class IteratorStream(AsyncIteratorByteStream, IteratorByteStream):
    def __init__(self, stream: Iterable[bytes]):
        class Stream:
            def __iter__(self) -> Iterator[bytes]:
                for chunk in stream:
                    yield chunk

            async def __aiter__(self) -> AsyncIterator[bytes]:
                for chunk in stream:
                    yield chunk

        AsyncIteratorByteStream.__init__(self, stream=Stream())
        IteratorByteStream.__init__(self, stream=Stream())


def multipart_stream(
    data: dict, files: Any, boundary: Optional[bytes]
) -> Union[httpx.AsyncByteStream, httpx.SyncByteStream]:
    warnings.warn(
        "data, files and boundary parameters will be removed in a future version. Use stream parameter with an instance of httpx._multipart.MultipartStream instead.",
        DeprecationWarning,
    )
    # import is performed at runtime when needed to reduce impact of internal changes in httpx
    from httpx._multipart import MultipartStream

    return MultipartStream(data=data or {}, files=files, boundary=boundary)
