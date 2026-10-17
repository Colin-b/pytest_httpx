from dataclasses import dataclass
from functools import cache
from types import ModuleType
from typing import TYPE_CHECKING, Literal


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
        import httpcore2 as httpcore2_  # pragma: no cover
        import httpx2 as httpx2_  # pragma: no cover
    except ModuleNotFoundError:  # pragma: no cover
        pass
    else:
        backends.append(HTTPXBackend("httpx2", httpx2_, httpcore2_))  # pragma: no cover

    try:
        import httpcore as httpcore_  # pragma: no cover
        import httpx as httpx_  # pragma: no cover
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


_BACKEND_ATTRIBUTE = "__pytest_httpx_backend"


def set_backend(request: "httpx.Request", backend: HTTPXBackend) -> None:
    # Store the intercepting backend on the request so that backend-agnostic
    # callbacks (e.g. the one built by `add_response`) can build a response
    # with the matching library.
    setattr(request, _BACKEND_ATTRIBUTE, backend)


def get_backend(request: "httpx.Request") -> HTTPXBackend:
    return getattr(request, _BACKEND_ATTRIBUTE)


if TYPE_CHECKING:
    import httpcore  # noqa: F401
    import httpx
    import httpx2  # noqa: F401
