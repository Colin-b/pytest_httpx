from typing import AsyncIterable, Dict, Iterable, Sequence, Tuple, Union


import httpx

# Those types are internally defined within httpx._types
HeaderTypes = Union[
    httpx.Headers,
    Dict[str, str],
    Dict[bytes, bytes],
    Sequence[Tuple[str, str]],
    Sequence[Tuple[bytes, bytes]],
]
ResponseContent = Union[str, bytes, Iterable[bytes], AsyncIterable[bytes]]
