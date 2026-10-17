import httpx
import pytest

from pytest_httpx import HTTPXMock

pytestmark = [
    pytest.mark.parametrize(
        "headers",
        [
            {},
            {"Content-Type": "multipart/form-data; boundary=test-boundary"},
            {"Content-Type": "multipart/form-data; boundary=ABCDEF012345"},
            {
                "Content-Type": 'multipart/form-data; boundary="test:boundary with space"'
            },
        ],
        ids=["default", "custom", "uppercase", "quoted"],
    ),
    pytest.mark.parametrize("data", [{}, {"field": "value"}], ids=["files", "data"]),
]


def mismatched_bodies(data: dict[str, str]) -> list[dict]:
    return [
        {"match_files": {"other": ("file_name", b"File content")}, "match_data": data},
        {"match_files": {"name": ("other", b"File content")}, "match_data": data},
        {"match_files": {"name": ("file_name", b"other")}, "match_data": data},
        {
            "match_files": {"name": ("file_name", b"File content")},
            "match_data": {"field": "other"},
        },
    ]


def register_responses(httpx_mock: HTTPXMock, data: dict[str, str]) -> None:
    for mismatch in mismatched_bodies(data):
        httpx_mock.add_response(**mismatch, status_code=400, is_optional=True)
    httpx_mock.add_response(
        match_files={"name": ("file_name", b"File content")},
        match_data=data,
        status_code=201,
    )


def assert_requests(
    httpx_mock: HTTPXMock, response: httpx.Response, data: dict[str, str]
) -> None:
    assert httpx_mock.get_requests(
        match_files={"name": ("file_name", b"File content")}, match_data=data
    ) == [response.request]
    for mismatch in mismatched_bodies(data):
        assert httpx_mock.get_requests(**mismatch) == []


def test_response_matching(
    httpx_mock: HTTPXMock, headers: dict[str, str], data: dict[str, str]
) -> None:
    register_responses(httpx_mock, data)

    with httpx.Client() as client:
        response = client.put(
            "https://test_url",
            headers=headers,
            files={"name": ("file_name", b"File content")},
            data=data,
        )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_response_matching_async(
    httpx_mock: HTTPXMock, headers: dict[str, str], data: dict[str, str]
) -> None:
    register_responses(httpx_mock, data)

    async with httpx.AsyncClient() as client:
        response = await client.put(
            "https://test_url",
            headers=headers,
            files={"name": ("file_name", b"File content")},
            data=data,
        )
    assert response.status_code == 201


def test_requests_retrieval(
    httpx_mock: HTTPXMock, headers: dict[str, str], data: dict[str, str]
) -> None:
    httpx_mock.add_response()

    with httpx.Client() as client:
        response = client.put(
            "https://test_url",
            headers=headers,
            files={"name": ("file_name", b"File content")},
            data=data,
        )
    assert_requests(httpx_mock, response, data)


@pytest.mark.asyncio
async def test_requests_retrieval_async(
    httpx_mock: HTTPXMock, headers: dict[str, str], data: dict[str, str]
) -> None:
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        response = await client.put(
            "https://test_url",
            headers=headers,
            files={"name": ("file_name", b"File content")},
            data=data,
        )
    assert_requests(httpx_mock, response, data)
