import gzip
from collections.abc import AsyncIterator, Iterator
from unittest.mock import Mock

import httpx
import pytest

from pytest_httpx import HTTPXMock


@pytest.fixture(params=[False, True], ids=["sync-client", "async-client"])
def asynchronous(request: pytest.FixtureRequest) -> bool:
    return request.param


async def send(asynchronous: bool, **kwargs) -> httpx.Response:
    if asynchronous:
        async with httpx.AsyncClient() as client:
            return await client.request(**kwargs)
    with httpx.Client() as client:
        return client.request(**kwargs)


@pytest.mark.asyncio
async def test_runtime_matcher_decodes_streamed_body(
    httpx_mock: HTTPXMock, asynchronous: bool
) -> None:
    httpx_mock.add_response(
        match_request=lambda request: gzip.decompress(request.content) == b"first",
        text="first response",
    )
    httpx_mock.add_response(
        match_request=lambda request: gzip.decompress(request.content) == b"second",
        text="second response",
    )

    def content(encoded: bytes) -> Iterator[bytes]:
        yield encoded[:10]
        yield encoded[10:]

    async def async_content(encoded: bytes) -> AsyncIterator[bytes]:
        for part in content(encoded):
            yield part

    for value in (b"second", b"first"):
        encoded = gzip.compress(value)

        response = await send(
            asynchronous,
            method="POST",
            url="https://test_url",
            content=async_content(encoded) if asynchronous else content(encoded),
            headers={"Content-Encoding": "gzip"},
        )
        assert response.text == f"{value.decode()} response"


@pytest.mark.asyncio
async def test_runtime_matcher_runs_after_existing_matchers(
    httpx_mock: HTTPXMock, asynchronous: bool
) -> None:
    predicate = Mock(return_value=True)
    httpx_mock.add_response(
        url="https://test_url/expected",
        method="POST",
        match_content=b"expected",
        match_request=predicate,
        text="matched",
    )
    httpx_mock.add_response(text="fallback", is_reusable=True)

    response = await send(
        asynchronous, method="POST", url="https://test_url/other", content=b"expected"
    )
    assert response.text == "fallback"
    response = await send(
        asynchronous, method="GET", url="https://test_url/expected", content=b"expected"
    )
    assert response.text == "fallback"
    response = await send(
        asynchronous, method="POST", url="https://test_url/expected", content=b"other"
    )
    assert response.text == "fallback"
    predicate.assert_not_called()

    response = await send(
        asynchronous,
        method="POST",
        url="https://test_url/expected",
        content=b"expected",
    )
    assert response.text == "matched"
    predicate.assert_called_once_with(httpx_mock.get_requests()[-1])


@pytest.mark.asyncio
async def test_runtime_matcher_can_match_header_absence(
    httpx_mock: HTTPXMock, asynchronous: bool
) -> None:
    httpx_mock.add_response(
        match_request=lambda request: "X-Optional" not in request.headers,
        status_code=204,
    )
    httpx_mock.add_response(status_code=201)

    response = await send(
        asynchronous,
        method="GET",
        url="https://test_url",
        headers={"X-Optional": "present"},
    )
    assert response.status_code == 201
    response = await send(asynchronous, method="GET", url="https://test_url")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_runtime_matcher_filters_recorded_requests(
    httpx_mock: HTTPXMock, asynchronous: bool
) -> None:
    httpx_mock.add_response(is_reusable=True)
    for content in (b"first", b"second"):
        await send(asynchronous, method="POST", url="https://test_url", content=content)

    requests = httpx_mock.get_requests(
        match_request=lambda request: request.content.startswith(b"s")
    )
    assert len(requests) == 1
    assert requests[0].content == b"second"
    assert (
        httpx_mock.get_request(
            match_request=lambda request: request.content == b"first"
        )
        is httpx_mock.get_requests()[0]
    )
    assert httpx_mock.get_request(match_request=lambda request: False) is None


@pytest.mark.asyncio
async def test_runtime_matcher_selects_reusable_callback(
    httpx_mock: HTTPXMock, asynchronous: bool
) -> None:
    def callback(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=request.content)

    httpx_mock.add_callback(
        callback,
        match_request=lambda request: request.content == b"expected",
        is_reusable=True,
    )
    for _ in range(2):
        response = await send(
            asynchronous, method="POST", url="https://test_url", content=b"expected"
        )
        assert response.content == b"expected"


@pytest.mark.asyncio
async def test_runtime_matcher_selects_exception(
    httpx_mock: HTTPXMock, asynchronous: bool
) -> None:
    httpx_mock.add_exception(
        httpx.ConnectError("unavailable"),
        match_request=lambda request: request.headers.get("X-Server") == "unavailable",
    )
    httpx_mock.add_response()
    response = await send(asynchronous, method="GET", url="https://test_url")
    assert response.status_code == 200
    with pytest.raises(httpx.ConnectError, match="unavailable"):
        await send(
            asynchronous,
            method="GET",
            url="https://test_url",
            headers={"X-Server": "unavailable"},
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_runtime_matcher_is_described_when_no_response_matches(
    httpx_mock: HTTPXMock, asynchronous: bool
) -> None:
    httpx_mock.add_response(match_request=lambda request: False, is_optional=True)
    with pytest.raises(httpx.TimeoutException, match="custom request matcher"):
        await send(asynchronous, method="GET", url="https://test_url")


@pytest.mark.asyncio
async def test_runtime_matcher_exception_propagates(
    httpx_mock: HTTPXMock, asynchronous: bool
) -> None:
    def fail(request: httpx.Request) -> bool:
        raise ValueError("cannot decode request body")

    httpx_mock.add_response(match_request=fail, is_optional=True)
    with pytest.raises(ValueError, match="cannot decode request body"):
        await send(asynchronous, method="GET", url="https://test_url")


@pytest.mark.asyncio
@pytest.mark.parametrize("result", [None, 1])
async def test_runtime_matcher_requires_boolean_result(
    httpx_mock: HTTPXMock, asynchronous: bool, result
) -> None:
    httpx_mock.add_response(match_request=lambda request: result, is_optional=True)
    with pytest.raises(TypeError, match="match_request must return a boolean"):
        await send(asynchronous, method="GET", url="https://test_url")


@pytest.mark.asyncio
async def test_runtime_matcher_rejects_coroutine_without_unawaited_warning(
    httpx_mock: HTTPXMock, asynchronous: bool, recwarn: pytest.WarningsRecorder
) -> None:
    async def predicate(request: httpx.Request) -> bool:
        return True

    httpx_mock.add_response(match_request=predicate, is_optional=True)
    with pytest.raises(TypeError, match="match_request must return a boolean"):
        await send(asynchronous, method="GET", url="https://test_url")
    assert not recwarn
