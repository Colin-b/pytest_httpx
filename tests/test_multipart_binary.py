import httpx
import pytest

from pytest_httpx import HTTPXMock


@pytest.fixture(params=[b"\xff", b"caf\xc3\xa9", b"ascii\x80suffix"])
def body(request: pytest.FixtureRequest) -> bytes:
    return b"--" + request.param + b"\r\nopaque binary document"


def test_binary_response_fallback(httpx_mock: HTTPXMock, body: bytes) -> None:
    httpx_mock.add_response(
        match_files={"upload": ("sample.txt", b"payload")},
        status_code=400,
        is_optional=True,
    )
    httpx_mock.add_response(match_content=body, status_code=202)

    with httpx.Client() as client:
        response = client.post(
            "https://test_url",
            content=body,
            headers={"Content-Type": "application/octet-stream"},
        )
    assert response.status_code == 202


@pytest.mark.asyncio
async def test_binary_response_fallback_async(
    httpx_mock: HTTPXMock, body: bytes
) -> None:
    httpx_mock.add_response(
        match_files={"upload": ("sample.txt", b"payload")},
        status_code=400,
        is_optional=True,
    )
    httpx_mock.add_response(match_content=body, status_code=202)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://test_url",
            content=body,
            headers={"Content-Type": "application/octet-stream"},
        )
    assert response.status_code == 202


def test_binary_requests_retrieval(httpx_mock: HTTPXMock, body: bytes) -> None:
    httpx_mock.add_response()

    with httpx.Client() as client:
        response = client.post(
            "https://test_url",
            content=body,
            headers={"Content-Type": "application/octet-stream"},
        )
    assert httpx_mock.get_requests(match_content=body) == [response.request]
    assert (
        httpx_mock.get_requests(match_files={"upload": ("sample.txt", b"payload")})
        == []
    )


@pytest.mark.asyncio
async def test_binary_requests_retrieval_async(
    httpx_mock: HTTPXMock, body: bytes
) -> None:
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://test_url",
            content=body,
            headers={"Content-Type": "application/octet-stream"},
        )
    assert httpx_mock.get_requests(match_content=body) == [response.request]
    assert (
        httpx_mock.get_requests(match_files={"upload": ("sample.txt", b"payload")})
        == []
    )
