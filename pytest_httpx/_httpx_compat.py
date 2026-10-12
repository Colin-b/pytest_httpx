import warnings
from dataclasses import dataclass
from functools import cache
from types import ModuleType
from typing import TYPE_CHECKING, Literal


class PytestHTTPXDeprecationWarning(UserWarning):
    pass


@dataclass(frozen=True)
class HTTPXBackend:
    name: Literal["httpx", "httpx2"]
    httpx: ModuleType
    httpcore: ModuleType


@cache
def get_backends() -> list[HTTPXBackend]:
    """Return every httpx backend found in the environment."""

    backends = []

    try:
        import httpcore2  # pragma: no cover
        import httpx2
    except ModuleNotFoundError:  # pragma: no cover
        pass
    else:
        backends.append(HTTPXBackend("httpx2", httpx2, httpcore2))  # pragma: no cover

    try:
        import httpcore as httpcore_  # pragma: no cover
        import httpx as httpx_
    except ModuleNotFoundError:  # pragma: no cover
        pass
    else:
        backends.append(HTTPXBackend("httpx", httpx_, httpcore_))  # pragma: no cover

    if not backends:  # pragma: no cover
        raise RuntimeError(
            "pytest-httpx requires either httpx or httpx2 to be installed.\n"
            "They are now optional dependencies, install the matching extra with:\n"
            "    $ pip install pytest-httpx[httpx2]\n"
            "or:\n"
            "    $ pip install pytest-httpx[httpx]\n"
        )

    return backends


if TYPE_CHECKING:
    import httpcore2 as httpcore
    import httpx2 as httpx
else:
    # A module-level backend for global httpx/httpcore names references.
    _backends = get_backends()
    [_default_backend, *_] = _backends
    httpx = _default_backend.httpx
    httpcore = _default_backend.httpcore

    if any(backend.name == "httpx" for backend in _backends):  # pragma: no cover
        warnings.warn(
            "Using httpx with pytest-httpx is deprecated; consider using httpx2 instead.",
            PytestHTTPXDeprecationWarning,
            stacklevel=2,
        )
