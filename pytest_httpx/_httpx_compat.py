import warnings
from dataclasses import dataclass
from functools import cache
from types import ModuleType
from typing import TYPE_CHECKING, Literal


class PytestHTTPXDeprecationWarning(UserWarning):
    pass


@dataclass(frozen=True)
class HttpxBackend:
    name: Literal["httpx", "httpx2"]
    httpx: ModuleType
    httpcore: ModuleType


@cache
def get_backends() -> list[HttpxBackend]:
    """Return every httpx backend found in the environment."""

    backends = []

    try:
        import httpx2
        import httpcore2
    except ModuleNotFoundError:
        pass
    else:
        backends.append(HttpxBackend("httpx2", httpx2, httpcore2))

    try:
        import httpx as httpx_
        import httpcore as httpcore_
    except ModuleNotFoundError:
        pass
    else:
        backends.append(HttpxBackend("httpx", httpx_, httpcore_))

    if not backends:
        raise RuntimeError(
            "pytest-httpx requires either httpx or httpx2 to be installed.\n"
            "They are now optional dependencies, install the matching extra with:\n"
            "    $ pip install pytest-httpx[httpx2]\n"
            "or:\n"
            "    $ pip install pytest-httpx[httpx]\n"
        )

    return backends


if TYPE_CHECKING:
    import httpx2 as httpx
    import httpcore2 as httpcore
else:
    # A module-level backend for global httpx/httpcore names references.
    _backends = get_backends()
    [_default_backend, *_] = _backends
    httpx = _default_backend.httpx
    httpcore = _default_backend.httpcore

    if any(backend.name == "httpx" for backend in _backends):
        warnings.warn(
            "Using httpx with pytest-httpx is deprecated; consider using httpx2 instead.",
            PytestHTTPXDeprecationWarning,
            stacklevel=2,
        )
