from typing import Union, Dict, Sequence, Tuple, Optional, List

import httpcore

# Those types are internally defined within httpcore._types
URL = Tuple[bytes, bytes, Optional[int], bytes]
Headers = List[Tuple[bytes, bytes]]
TimeoutDict = Dict[str, Optional[float]]

Response = Tuple[
    int, Headers, Union[httpcore.SyncByteStream, httpcore.AsyncByteStream], dict
]

# Those types are internally defined within httpx._types
HeaderTypes = Union[
    "Headers",
    Dict[str, str],
    Dict[bytes, bytes],
    Sequence[Tuple[str, str]],
    Sequence[Tuple[bytes, bytes]],
]


class IteratorStream(httpcore.AsyncIteratorByteStream, httpcore.IteratorByteStream):
    def __init__(self, iterator):
        httpcore.AsyncIteratorByteStream.__init__(self, aiterator=iterator)
        httpcore.IteratorByteStream.__init__(self, iterator=iterator)


def stream(
    data, files, boundary: bytes
) -> Union[httpcore.AsyncByteStream, httpcore.SyncByteStream]:
    if files:
        # TODO Get rid of this internal import
        # import is performed at runtime when needed to reduce impact of internal changes in httpx
        from httpx._multipart import MultipartStream

        return MultipartStream(data=data or {}, files=files, boundary=boundary)

    if isinstance(data, str):
        data = data.encode("utf-8")
    elif data is None:
        data = b""

    if isinstance(data, bytes):
        return httpcore.PlainByteStream(data)

    return IteratorStream(data)
