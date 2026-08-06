import warnings
from typing import TYPE_CHECKING


class PytestHTTPXDeprecationWarning(UserWarning):
    pass


if TYPE_CHECKING:
    import httpx2 as httpx
    import httpcore2 as httpcore
else:
    try:
        import httpx2 as httpx
        import httpcore2 as httpcore
    except ModuleNotFoundError:
        try:
            import httpx  # noqa: F401
            import httpcore  # noqa: F401
        except ModuleNotFoundError:
            raise RuntimeError(
                "pytest-httpx requires the httpx2 package to be installed.\n"
                "You can install it with:\n"
                "    $ pip install httpx2\n"
            ) from None
        else:
            warnings.warn(
                "Using `httpx` with pytest-httpx is deprecated; install `httpx2` instead.",
                PytestHTTPXDeprecationWarning,
                stacklevel=2,
            )
