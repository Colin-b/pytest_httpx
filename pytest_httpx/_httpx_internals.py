from typing import Union, Any, Iterator, AsyncIterator
from json import dumps

import httpcore


class ByteStream(httpcore.AsyncByteStream, httpcore.SyncByteStream):
    def __init__(self, data: bytes):
        httpcore.AsyncByteStream.__init__(self)
        httpcore.SyncByteStream.__init__(self)
        self.data = data

    def __iter__(self) -> Iterator[bytes]:
        yield self.data

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield self.data


class IteratorStream(httpcore.AsyncByteStream, httpcore.SyncByteStream):
    def __init__(self, iterator):
        httpcore.AsyncByteStream.__init__(self, aiterator=iterator)
        httpcore.SyncByteStream.__init__(self, iterator=iterator)


def stream(
    data, files, json: Any, boundary: bytes
) -> Union[httpcore.AsyncByteStream, httpcore.SyncByteStream]:
    if files:
        # TODO Get rid of this internal import
        # import is performed at runtime when needed to reduce impact of internal changes in httpx
        from httpx._content_streams import MultipartStream

        return MultipartStream(data=data or {}, files=files, boundary=boundary)

    if json is not None:
        data = dumps(json).encode("utf-8")
    elif isinstance(data, str):
        data = data.encode("utf-8")
    elif data is None:
        data = b""

    if isinstance(data, bytes):
        return ByteStream(data)

    return IteratorStream(data)
