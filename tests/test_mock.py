import pytest

from pytest_httpx import httpx_mock, HTTPXMock


@pytest.mark.xfail(
    raises=AssertionError, reason="Unused responses should fail test case."
)
def test_httpx_mock_unused_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")


@pytest.mark.xfail(
    raises=AssertionError, reason="Unused callbacks should fail test case."
)
def test_httpx_mock_unused_callback(httpx_mock: HTTPXMock):
    httpx_mock.add_callback(lambda r, t: None, "http://test_url")
