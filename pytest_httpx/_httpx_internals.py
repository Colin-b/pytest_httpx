from typing import Union, Any
from json import dumps

import httpcore


class IteratorStream(httpcore.AsyncIteratorByteStream, httpcore.IteratorByteStream):
    def __init__(self, iterator):
        httpcore.AsyncIteratorByteStream.__init__(self, aiterator=iterator)
        httpcore.IteratorByteStream.__init__(self, iterator=iterator)


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
        return httpcore.PlainByteStream(data)

    return IteratorStream(data)
