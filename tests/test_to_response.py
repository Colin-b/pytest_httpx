import pytest

import pytest_httpx


def test_default_response():
    with pytest.warns(
        DeprecationWarning,
        match="pytest_httpx.to_response will be removed in a future version. Use httpx.Response instead.",
    ):
        default_response = pytest_httpx.to_response()
    assert default_response.status_code == 200
    assert default_response.extensions == {"http_version": b"HTTP/1.1"}
