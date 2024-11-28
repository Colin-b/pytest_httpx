import asyncio
import math
import os
import re
import time
from collections.abc import AsyncIterable

import httpx
import pytest
from pytest import Testdir
from unittest.mock import ANY

import pytest_httpx
from pytest_httpx import HTTPXMock


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_without_response(httpx_mock: HTTPXMock) -> None:
    with pytest.raises(Exception) as exception_info:
        async with httpx.AsyncClient() as client:
            await client.get("https://test_url")
    assert (
        str(exception_info.value)
        == """No response can be found for GET request on https://test_url"""
    )


@pytest.mark.asyncio
async def test_default_response(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
    assert response.content == b""
    assert response.status_code == 200
    assert response.headers == httpx.Headers({})
    assert response.http_version == "HTTP/1.1"


@pytest.mark.asyncio
async def test_url_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b""


@pytest.mark.asyncio
async def test_url_matching_reusing_response(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b""

        response = await client.post("https://test_url")
        assert response.content == b""


@pytest.mark.asyncio
async def test_url_query_string_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url?a=1&b=2", is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url?a=1&b=2")
        assert response.content == b""

        # Parameters order should not matter
        response = await client.get("https://test_url?b=2&a=1")
        assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_url_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", is_optional=True)

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get("https://test_url2")
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url2 amongst:
- Match any request on https://test_url"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_url_query_string_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url?a=1&a=2", is_optional=True)

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            # Same parameter order matters as it corresponds to a list on server side
            await client.get("https://test_url?a=2&a=1")
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url?a=2&a=1 amongst:
- Match any request on https://test_url?a=1&a=2"""
        )


@pytest.mark.asyncio
async def test_method_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="get", is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b""

        response = await client.get("https://test_url2")
        assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_method_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="get", is_optional=True)

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url")
        assert (
            str(exception_info.value)
            == """No response can be found for POST request on https://test_url amongst:
- Match GET request"""
        )


@pytest.mark.asyncio
async def test_reusing_one_response(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url", content=b"test content", is_reusable=True
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b"test content"

        response = await client.get("https://test_url")
        assert response.content == b"test content"


@pytest.mark.asyncio
async def test_response_with_string_body(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", text="test content")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b"test content"


@pytest.mark.asyncio
async def test_response_with_html_string_body(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", html="<body>test content</body>")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b"<body>test content</body>"


@pytest.mark.asyncio
async def test_stream_response_streaming(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        stream=pytest_httpx.IteratorStream([b"part 1", b"part 2"]),
        is_reusable=True,
    )

    async with httpx.AsyncClient() as client:
        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1",
                b"part 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for _ in response.aiter_raw():
                    pass  # pragma: no cover

        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1",
                b"part 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for _ in response.aiter_raw():
                    pass  # pragma: no cover


@pytest.mark.asyncio
async def test_content_response_streaming(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        content=b"part 1 and 2",
        is_reusable=True,
    )

    async with httpx.AsyncClient() as client:
        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1 and 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for _ in response.aiter_raw():
                    pass  # pragma: no cover

        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1 and 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for _ in response.aiter_raw():
                    pass  # pragma: no cover


@pytest.mark.asyncio
async def test_text_response_streaming(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        text="part 1 and 2",
        is_reusable=True,
    )

    async with httpx.AsyncClient() as client:
        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1 and 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for _ in response.aiter_raw():
                    pass  # pragma: no cover

        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1 and 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for _ in response.aiter_raw():
                    pass  # pragma: no cover


@pytest.mark.asyncio
async def test_default_response_streaming(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == []
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for _ in response.aiter_raw():
                    pass  # pragma: no cover

        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == []
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for _ in response.aiter_raw():
                    pass  # pragma: no cover


@pytest.mark.asyncio
async def test_with_many_responses(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", content=b"test content 1")
    httpx_mock.add_response(url="https://test_url", content=b"test content 2")
    httpx_mock.add_response(url="https://test_url", content=b"test content 2")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b"test content 1"

        response = await client.get("https://test_url")
        assert response.content == b"test content 2"

        response = await client.get("https://test_url")
        assert response.content == b"test content 2"


@pytest.mark.asyncio
async def test_with_many_reused_responses(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", content=b"test content 1")
    httpx_mock.add_response(
        url="https://test_url", content=b"test content 2", is_reusable=True
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b"test content 1"

        response = await client.get("https://test_url")
        assert response.content == b"test content 2"

        response = await client.get("https://test_url")
        assert response.content == b"test content 2"


@pytest.mark.asyncio
async def test_with_many_responses_methods(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url", method="GET", content=b"test content 1"
    )
    httpx_mock.add_response(
        url="https://test_url", method="POST", content=b"test content 2"
    )
    httpx_mock.add_response(
        url="https://test_url", method="PUT", content=b"test content 3"
    )
    httpx_mock.add_response(
        url="https://test_url", method="DELETE", content=b"test content 4"
    )
    httpx_mock.add_response(
        url="https://test_url", method="PATCH", content=b"test content 5"
    )
    httpx_mock.add_response(
        url="https://test_url", method="HEAD", content=b"test content 6"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url")
        assert response.content == b"test content 2"

        response = await client.get("https://test_url")
        assert response.content == b"test content 1"

        response = await client.put("https://test_url")
        assert response.content == b"test content 3"

        response = await client.head("https://test_url")
        assert response.content == b"test content 6"

        response = await client.patch("https://test_url")
        assert response.content == b"test content 5"

        response = await client.delete("https://test_url")
        assert response.content == b"test content 4"


@pytest.mark.asyncio
async def test_with_many_responses_status_codes(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url", method="GET", content=b"test content 1", status_code=200
    )
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        content=b"test content 2",
        status_code=201,
    )
    httpx_mock.add_response(
        url="https://test_url", method="PUT", content=b"test content 3", status_code=202
    )
    httpx_mock.add_response(
        url="https://test_url",
        method="DELETE",
        content=b"test content 4",
        status_code=303,
    )
    httpx_mock.add_response(
        url="https://test_url",
        method="PATCH",
        content=b"test content 5",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://test_url",
        method="HEAD",
        content=b"test content 6",
        status_code=500,
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url")
        assert response.content == b"test content 2"
        assert response.status_code == 201

        response = await client.get("https://test_url")
        assert response.content == b"test content 1"
        assert response.status_code == 200

        response = await client.put("https://test_url")
        assert response.content == b"test content 3"
        assert response.status_code == 202

        response = await client.head("https://test_url")
        assert response.content == b"test content 6"
        assert response.status_code == 500

        response = await client.patch("https://test_url")
        assert response.content == b"test content 5"
        assert response.status_code == 404

        response = await client.delete("https://test_url")
        assert response.content == b"test content 4"
        assert response.status_code == 303


@pytest.mark.asyncio
async def test_with_many_responses_urls_str(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url?param1=test", method="GET", content=b"test content 1"
    )
    httpx_mock.add_response(
        url="https://test_url?param2=test", method="POST", content=b"test content 2"
    )
    httpx_mock.add_response(
        url="https://test_url?param3=test", method="PUT", content=b"test content 3"
    )
    httpx_mock.add_response(
        url="https://test_url?param4=test", method="DELETE", content=b"test content 4"
    )
    httpx_mock.add_response(
        url="https://test_url?param5=test", method="PATCH", content=b"test content 5"
    )
    httpx_mock.add_response(
        url="https://test_url?param6=test", method="HEAD", content=b"test content 6"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            httpx.URL("https://test_url", params={"param2": "test"})
        )
        assert response.content == b"test content 2"

        response = await client.get(
            httpx.URL("https://test_url", params={"param1": "test"})
        )
        assert response.content == b"test content 1"

        response = await client.put(
            httpx.URL("https://test_url", params={"param3": "test"})
        )
        assert response.content == b"test content 3"

        response = await client.head(
            httpx.URL("https://test_url", params={"param6": "test"})
        )
        assert response.content == b"test content 6"

        response = await client.patch(
            httpx.URL("https://test_url", params={"param5": "test"})
        )
        assert response.content == b"test content 5"

        response = await client.delete(
            httpx.URL("https://test_url", params={"param4": "test"})
        )
        assert response.content == b"test content 4"


@pytest.mark.asyncio
async def test_response_with_pattern_in_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url=re.compile(".*test.*"))
    httpx_mock.add_response(url="https://unmatched", content=b"test content")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://unmatched")
        assert response.content == b"test content"

        response = await client.get("https://test_url")
        assert response.content == b""


@pytest.mark.asyncio
async def test_request_with_pattern_in_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url")
    httpx_mock.add_response(url="https://unmatched")

    async with httpx.AsyncClient() as client:
        await client.get("https://unmatched")
        await client.get("https://test_url", headers={"X-Test": "1"})

    assert httpx_mock.get_request(url=re.compile(".*test.*")).headers["x-test"] == "1"


@pytest.mark.asyncio
async def test_requests_with_pattern_in_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url")
    httpx_mock.add_response(url="https://tests_url")
    httpx_mock.add_response(url="https://unmatched")

    async with httpx.AsyncClient() as client:
        await client.get("https://tests_url", headers={"X-Test": "1"})
        await client.get("https://unmatched", headers={"X-Test": "2"})
        await client.get("https://test_url")

    requests = httpx_mock.get_requests(url=re.compile(".*test.*"))
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "1"
    assert "x-test" not in requests[1].headers


@pytest.mark.asyncio
async def test_callback_with_pattern_in_url(httpx_mock: HTTPXMock) -> None:
    def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"url": str(request.url)})

    def custom_response2(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            extensions={"http_version": b"HTTP/2.0"},
            json={"url": str(request.url)},
        )

    httpx_mock.add_callback(custom_response, url=re.compile(".*test.*"))
    httpx_mock.add_callback(custom_response2, url="https://unmatched")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://unmatched")
        assert response.http_version == "HTTP/2.0"

        response = await client.get("https://test_url")
        assert response.http_version == "HTTP/1.1"


@pytest.mark.asyncio
async def test_async_callback_with_await_statement(httpx_mock: HTTPXMock) -> None:
    async def simulate_network_latency(request: httpx.Request):
        await asyncio.sleep(1)
        return httpx.Response(
            status_code=200,
            json={"url": str(request.url), "time": time.time()},
        )

    def instant_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200, json={"url": str(request.url), "time": time.time()}
        )

    httpx_mock.add_callback(simulate_network_latency)
    httpx_mock.add_callback(instant_response)
    httpx_mock.add_response(json={"url": "not a callback"})

    async with httpx.AsyncClient() as client:
        responses = await asyncio.gather(
            client.get("https://slow"),
            client.get("https://fast_with_callback"),
            client.get("https://fast_with_response"),
        )
        slow_response = responses[0].json()
        assert slow_response["url"] == "https://slow"

        fast_callback_response = responses[1].json()
        assert fast_callback_response["url"] == "https://fast_with_callback"

        fast_response = responses[2].json()
        assert fast_response["url"] == "not a callback"

        # Ensure slow request was properly awaited (did not block subsequent async queries)
        assert math.isclose(slow_response["time"], fast_callback_response["time"] + 1)


@pytest.mark.asyncio
async def test_async_callback_with_pattern_in_url(httpx_mock: HTTPXMock) -> None:
    async def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"url": str(request.url)})

    async def custom_response2(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            extensions={"http_version": b"HTTP/2.0"},
            json={"url": str(request.url)},
        )

    httpx_mock.add_callback(custom_response, url=re.compile(".*test.*"))
    httpx_mock.add_callback(custom_response2, url="https://unmatched")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://unmatched")
        assert response.http_version == "HTTP/2.0"

        response = await client.get("https://test_url")
        assert response.http_version == "HTTP/1.1"


@pytest.mark.asyncio
async def test_with_many_responses_urls_instances(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url=httpx.URL("https://test_url", params={"param1": "test"}),
        method="GET",
        content=b"test content 1",
    )
    httpx_mock.add_response(
        url=httpx.URL("https://test_url", params={"param2": "test"}),
        method="POST",
        content=b"test content 2",
    )
    httpx_mock.add_response(
        url=httpx.URL("https://test_url", params={"param3": "test"}),
        method="PUT",
        content=b"test content 3",
    )
    httpx_mock.add_response(
        url=httpx.URL("https://test_url", params={"param4": "test"}),
        method="DELETE",
        content=b"test content 4",
    )
    httpx_mock.add_response(
        url=httpx.URL("https://test_url", params={"param5": "test"}),
        method="PATCH",
        content=b"test content 5",
    )
    httpx_mock.add_response(
        url=httpx.URL("https://test_url", params={"param6": "test"}),
        method="HEAD",
        content=b"test content 6",
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url?param2=test")
        assert response.content == b"test content 2"

        response = await client.get("https://test_url?param1=test")
        assert response.content == b"test content 1"

        response = await client.put("https://test_url?param3=test")
        assert response.content == b"test content 3"

        response = await client.head("https://test_url?param6=test")
        assert response.content == b"test content 6"

        response = await client.patch("https://test_url?param5=test")
        assert response.content == b"test content 5"

        response = await client.delete("https://test_url?param4=test")
        assert response.content == b"test content 4"


@pytest.mark.asyncio
async def test_with_http_version_2(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url", http_version="HTTP/2", content=b"test content 1"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b"test content 1"
        assert response.http_version == "HTTP/2"


@pytest.mark.asyncio
async def test_with_headers(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        content=b"test content 1",
        headers={"X-Test": "Test value"},
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b"test content 1"
        assert response.headers == httpx.Headers(
            {"x-test": "Test value", "content-length": "14"}
        )


@pytest.mark.asyncio
async def test_requests_retrieval(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url", method="GET", content=b"test content 1"
    )
    httpx_mock.add_response(
        url="https://test_url", method="POST", content=b"test content 2"
    )
    httpx_mock.add_response(
        url="https://test_url", method="PUT", content=b"test content 3"
    )
    httpx_mock.add_response(
        url="https://test_url", method="DELETE", content=b"test content 4"
    )
    httpx_mock.add_response(
        url="https://test_url", method="PATCH", content=b"test content 5"
    )
    httpx_mock.add_response(
        url="https://test_url", method="HEAD", content=b"test content 6"
    )

    async with httpx.AsyncClient() as client:
        await client.post("https://test_url", content=b"sent content 2")
        await client.get("https://test_url", headers={"X-TEST": "test header 1"})
        await client.put("https://test_url", content=b"sent content 3")
        await client.head("https://test_url")
        await client.patch("https://test_url", content=b"sent content 5")
        await client.delete("https://test_url", headers={"X-Test": "test header 4"})

    assert (
        httpx_mock.get_request(url=httpx.URL("https://test_url"), method="PATCH").read()
        == b"sent content 5"
    )
    assert (
        httpx_mock.get_request(url=httpx.URL("https://test_url"), method="HEAD").read()
        == b""
    )
    assert (
        httpx_mock.get_request(url=httpx.URL("https://test_url"), method="PUT").read()
        == b"sent content 3"
    )
    assert (
        httpx_mock.get_request(url=httpx.URL("https://test_url"), method="GET").headers[
            "x-test"
        ]
        == "test header 1"
    )
    assert (
        httpx_mock.get_request(url=httpx.URL("https://test_url"), method="POST").read()
        == b"sent content 2"
    )
    assert (
        httpx_mock.get_request(
            url=httpx.URL("https://test_url"), method="DELETE"
        ).headers["x-test"]
        == "test header 4"
    )


@pytest.mark.asyncio
async def test_requests_retrieval_on_same_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url", headers={"X-TEST": "test header 1"})
        await client.get("https://test_url", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests(url=httpx.URL("https://test_url"))
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


@pytest.mark.asyncio
async def test_request_retrieval_on_same_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url", headers={"X-TEST": "test header 1"})
        await client.get("https://test_url2", headers={"X-TEST": "test header 2"})

    request = httpx_mock.get_request(url=httpx.URL("https://test_url"))
    assert request.headers["x-test"] == "test header 1"


@pytest.mark.asyncio
async def test_requests_retrieval_on_same_method(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url", headers={"X-TEST": "test header 1"})
        await client.get("https://test_url2", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests(method="GET")
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


@pytest.mark.asyncio
async def test_request_retrieval_on_same_method(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url", headers={"X-TEST": "test header 1"})
        await client.post("https://test_url", headers={"X-TEST": "test header 2"})

    request = httpx_mock.get_request(method="GET")
    assert request.headers["x-test"] == "test header 1"


@pytest.mark.asyncio
async def test_requests_retrieval_on_same_url_and_method(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url", headers={"X-TEST": "test header 1"})
        await client.get("https://test_url", headers={"X-TEST": "test header 2"})
        await client.post("https://test_url", headers={"X-TEST": "test header 3"})
        await client.get("https://test_url2", headers={"X-TEST": "test header 4"})

    requests = httpx_mock.get_requests(url=httpx.URL("https://test_url"), method="GET")
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


@pytest.mark.asyncio
async def test_default_requests_retrieval(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.post("https://test_url", headers={"X-TEST": "test header 1"})
        await client.get("https://test_url2", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


@pytest.mark.asyncio
async def test_default_request_retrieval(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.post("https://test_url", headers={"X-TEST": "test header 1"})

    request = httpx_mock.get_request()
    assert request.headers["x-test"] == "test header 1"


@pytest.mark.asyncio
async def test_requests_json_body(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url", method="GET", json=["list content 1", "list content 2"]
    )
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        json={"key 1": "value 1", "key 2": "value 2"},
    )
    httpx_mock.add_response(url="https://test_url", method="PUT", json="string value")

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url")
        assert response.json() == {"key 1": "value 1", "key 2": "value 2"}
        assert response.headers["content-type"] == "application/json"

        response = await client.get("https://test_url")
        assert response.json() == ["list content 1", "list content 2"]
        assert response.headers["content-type"] == "application/json"

        response = await client.put("https://test_url")
        assert response.json() == "string value"
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_callback_raising_exception(httpx_mock: HTTPXMock) -> None:
    def raise_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(
            f"Unable to read within {request.extensions['timeout']['read']}",
            request=request,
        )

    httpx_mock.add_callback(raise_timeout, url="https://test_url")

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.ReadTimeout) as exception_info:
            await client.get("https://test_url")
        assert str(exception_info.value) == "Unable to read within 5.0"


@pytest.mark.asyncio
async def test_async_callback_raising_exception(httpx_mock: HTTPXMock) -> None:
    async def raise_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(
            f"Unable to read within {request.extensions['timeout']['read']}",
            request=request,
        )

    httpx_mock.add_callback(raise_timeout, url="https://test_url")

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.ReadTimeout) as exception_info:
            await client.get("https://test_url")
        assert str(exception_info.value) == "Unable to read within 5.0"


@pytest.mark.asyncio
async def test_request_exception_raising(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(
        httpx.ReadTimeout("Unable to read within 5.0"), url="https://test_url"
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.ReadTimeout) as exception_info:
            await client.get("https://test_url")
        assert str(exception_info.value) == "Unable to read within 5.0"
        assert exception_info.value.request is not None


@pytest.mark.asyncio
async def test_non_request_exception_raising(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(
        httpx.HTTPError("Unable to read within 5.0"), url="https://test_url"
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPError) as exception_info:
            await client.get("https://test_url")
        assert str(exception_info.value) == "Unable to read within 5.0"


@pytest.mark.asyncio
async def test_callback_returning_response(httpx_mock: HTTPXMock) -> None:
    def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"url": str(request.url)})

    httpx_mock.add_callback(custom_response, url="https://test_url")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == {"url": "https://test_url"}
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_async_callback_returning_response(httpx_mock: HTTPXMock) -> None:
    async def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"url": str(request.url)})

    httpx_mock.add_callback(custom_response, url="https://test_url")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == {"url": "https://test_url"}
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_callback_executed_twice(httpx_mock: HTTPXMock) -> None:
    def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=["content"])

    httpx_mock.add_callback(custom_response, is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"

        response = await client.post("https://test_url")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_async_callback_executed_twice(httpx_mock: HTTPXMock) -> None:
    async def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=["content"])

    httpx_mock.add_callback(custom_response, is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"

        response = await client.post("https://test_url")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_callback_registered_after_response(httpx_mock: HTTPXMock) -> None:
    def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=["content2"])

    httpx_mock.add_response(json=["content1"])
    httpx_mock.add_callback(custom_response, is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == ["content1"]
        assert response.headers["content-type"] == "application/json"

        response = await client.post("https://test_url")
        assert response.json() == ["content2"]
        assert response.headers["content-type"] == "application/json"

        # Assert that the last registered callback is sent again even if there is a response
        response = await client.post("https://test_url")
        assert response.json() == ["content2"]
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_async_callback_registered_after_response(httpx_mock: HTTPXMock) -> None:
    async def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=["content2"])

    httpx_mock.add_response(json=["content1"])
    httpx_mock.add_callback(custom_response, is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == ["content1"]
        assert response.headers["content-type"] == "application/json"

        response = await client.post("https://test_url")
        assert response.json() == ["content2"]
        assert response.headers["content-type"] == "application/json"

        # Assert that the last registered callback is sent again even if there is a response
        response = await client.post("https://test_url")
        assert response.json() == ["content2"]
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_response_registered_after_callback(httpx_mock: HTTPXMock) -> None:
    def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=["content1"])

    httpx_mock.add_callback(custom_response)
    httpx_mock.add_response(json=["content2"], is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == ["content1"]
        assert response.headers["content-type"] == "application/json"

        response = await client.post("https://test_url")
        assert response.json() == ["content2"]
        assert response.headers["content-type"] == "application/json"

        # Assert that the last registered response is sent again even if there is a callback
        response = await client.post("https://test_url")
        assert response.json() == ["content2"]
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_response_registered_after_async_callback(httpx_mock: HTTPXMock) -> None:
    async def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=["content1"])

    httpx_mock.add_callback(custom_response)
    httpx_mock.add_response(json=["content2"], is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == ["content1"]
        assert response.headers["content-type"] == "application/json"

        response = await client.post("https://test_url")
        assert response.json() == ["content2"]
        assert response.headers["content-type"] == "application/json"

        # Assert that the last registered response is sent again even if there is a callback
        response = await client.post("https://test_url")
        assert response.json() == ["content2"]
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_callback_matching_method(httpx_mock: HTTPXMock) -> None:
    def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=["content"])

    httpx_mock.add_callback(custom_response, method="GET", is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"

        response = await client.get("https://test_url2")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_async_callback_matching_method(httpx_mock: HTTPXMock) -> None:
    async def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=["content"])

    httpx_mock.add_callback(custom_response, method="GET", is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"

        response = await client.get("https://test_url2")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"


def test_request_retrieval_with_more_than_one(testdir: Testdir) -> None:
    """
    Single request cannot be returned if there is more than one matching.
    """
    testdir.makepyfile(
        """
        import httpx
        import pytest
        
        
        @pytest.mark.asyncio
        async def test_request_retrieval_with_more_than_one(httpx_mock):
            httpx_mock.add_response(is_reusable=True)
        
            async with httpx.AsyncClient() as client:
                await client.get("https://test_url", headers={"X-TEST": "test header 1"})
                await client.get("https://test_url", headers={"X-TEST": "test header 2"})
        
            httpx_mock.get_request(url=httpx.URL("https://test_url"))
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: More than one request (2) matched, use get_requests instead or refine your filters."
        ]
    )


@pytest.mark.asyncio
async def test_headers_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={"User-Agent": f"python-httpx/{httpx.__version__}"}
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b""


@pytest.mark.asyncio
async def test_multi_value_headers_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_headers={"my-custom-header": "value1, value2"})

    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://test_url",
            headers=[("my-custom-header", "value1"), ("my-custom-header", "value2")],
        )
        assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_multi_value_headers_not_matching_single_value_issued(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        match_headers={"my-custom-header": "value1"}, is_optional=True
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get(
                "https://test_url",
                headers=[
                    ("my-custom-header", "value1"),
                    ("my-custom-header", "value2"),
                ],
            )
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url with {'my-custom-header': 'value1, value2'} headers amongst:
- Match any request with {'my-custom-header': 'value1'} headers"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_multi_value_headers_not_matching_multi_value_issued(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        match_headers={"my-custom-header": "value1, value2"}, is_optional=True
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get(
                "https://test_url",
                headers=[
                    ("my-custom-header", "value1"),
                    ("my-custom-header", "value3"),
                ],
            )
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url with {'my-custom-header': 'value1, value3'} headers amongst:
- Match any request with {'my-custom-header': 'value1, value2'} headers"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_headers_matching_respect_case(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={"user-agent": f"python-httpx/{httpx.__version__}"},
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get("https://test_url")
        assert (
            str(exception_info.value)
            == f"""No response can be found for GET request on https://test_url with {{'User-Agent': 'python-httpx/{httpx.__version__}'}} headers amongst:
- Match any request with {{'user-agent': 'python-httpx/{httpx.__version__}'}} headers"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_headers_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
            "Host2": "test_url",
        },
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get("https://test_url")
        assert (
            str(exception_info.value)
            == f"""No response can be found for GET request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers amongst:
- Match any request with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2', 'Host2': 'test_url'}} headers"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_url_not_matching_upper_case_headers_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        method="GET",
        url="https://test_url?q=b",
        match_headers={"MyHeader": "Something"},
        is_optional=True,
    )
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get("https://test_url", headers={"MyHeader": "Something"})
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url with {'MyHeader': 'Something'} headers amongst:
- Match GET request on https://test_url?q=b with {'MyHeader': 'Something'} headers"""
        )


@pytest.mark.asyncio
async def test_content_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_content=b"This is the body")

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url", content=b"This is the body")
        assert response.read() == b""


@pytest.mark.asyncio
async def test_proxy_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(proxy_url="http://user:pwd@my_other_proxy/")

    async with httpx.AsyncClient(proxy="http://user:pwd@my_other_proxy") as client:
        response = await client.get("https://test_url")
        assert response.read() == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_proxy_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(proxy_url="http://my_test_proxy", is_optional=True)

    async with httpx.AsyncClient(proxy="http://my_test_proxy") as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get("http://test_url")
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on http://test_url with http://my_test_proxy/ proxy URL amongst:
- Match any request with http://my_test_proxy proxy URL"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_proxy_not_existing(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(proxy_url="http://my_test_proxy", is_optional=True)

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get("http://test_url")
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on http://test_url with no proxy URL amongst:
- Match any request with http://my_test_proxy proxy URL"""
        )


@pytest.mark.asyncio
async def test_requests_retrieval_content_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.post("https://test_url", content=b"This is the body")
        await client.post("https://test_url2", content=b"This is the body")
        await client.post("https://test_url2", content=b"This is the body2")

    assert len(httpx_mock.get_requests(match_content=b"This is the body")) == 2


@pytest.mark.asyncio
async def test_requests_retrieval_json_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.post("https://test_url", json=["my_str"])
        await client.post("https://test_url2", json=["my_str"])
        await client.post("https://test_url2", json=["my_str2"])

    assert len(httpx_mock.get_requests(match_json=["my_str"])) == 2


@pytest.mark.asyncio
async def test_requests_retrieval_proxy_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient(
        mounts={
            "http://": httpx.AsyncHTTPTransport(proxy="http://my_test_proxy"),
            "https://": httpx.AsyncHTTPTransport(
                proxy="http://user:pwd@my_other_proxy"
            ),
        }
    ) as client:
        await client.get("https://test_url")
        await client.get("https://test_url2")
        await client.get("http://test_url2")

    assert (
        len(httpx_mock.get_requests(proxy_url="http://user:pwd@my_other_proxy/")) == 2
    )


@pytest.mark.asyncio
async def test_request_retrieval_proxy_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient(
        mounts={
            "http://": httpx.AsyncHTTPTransport(proxy="http://my_test_proxy"),
            "https://": httpx.AsyncHTTPTransport(
                proxy="http://user:pwd@my_other_proxy"
            ),
        }
    ) as client:
        await client.get("https://test_url")
        await client.get("https://test_url2")
        await client.get("http://test_url2")

    assert httpx_mock.get_request(proxy_url="http://my_test_proxy/")


@pytest.mark.asyncio
async def test_requests_retrieval_files_and_data_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.put(
            "https://test_url",
            files={"name": ("file_name", b"File content")},
            data={"field1": "value"},
        )
        await client.put(
            "https://test_url2",
            files={"name": ("file_name", b"File content")},
            data={"field": "value"},
        )
        await client.put(
            "http://test_url2",
            files={"name": ("file_name", b"File content")},
            data={"field": "value"},
        )

    assert (
        len(
            httpx_mock.get_requests(
                match_files={"name": ("file_name", b"File content")},
                match_data={"field": "value"},
            )
        )
        == 2
    )


@pytest.mark.asyncio
async def test_request_retrieval_files_and_data_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.put(
            "https://test_url",
            files={"name": ("file_name", b"File content")},
            data={"field": "value"},
        )
        await client.get("https://test_url2")
        await client.get("http://test_url2")

    assert httpx_mock.get_request(
        match_files={"name": ("file_name", b"File content")},
        match_data={"field": "value"},
    )


@pytest.mark.asyncio
async def test_requests_retrieval_extensions_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url")
        await client.get("https://test_url2", timeout=10)
        await client.get("https://test_url2", timeout=10)
    assert (
        len(
            httpx_mock.get_requests(
                match_extensions={
                    "timeout": {"connect": 10, "read": 10, "write": 10, "pool": 10}
                }
            )
        )
        == 2
    )


@pytest.mark.asyncio
async def test_request_retrieval_extensions_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url", timeout=httpx.Timeout(5, read=10))
        await client.get("https://test_url2", timeout=10)
        await client.get("http://test_url2", timeout=10)

    assert httpx_mock.get_request(
        match_extensions={"timeout": {"connect": 5, "read": 10, "write": 5, "pool": 5}}
    )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_content_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_content=b"This is the body", is_optional=True)

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body2")
        assert (
            str(exception_info.value)
            == """No response can be found for POST request on https://test_url with b'This is the body2' body amongst:
- Match any request with b'This is the body' body"""
        )


@pytest.mark.asyncio
async def test_json_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_json={"a": 1, "b": 2})

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url", json={"b": 2, "a": 1})
        assert response.read() == b""


@pytest.mark.asyncio
async def test_json_partial_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_json={"a": 1, "b": ANY})

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url", json={"b": 2, "a": 1})
        assert response.read() == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_json_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_json={"a": 1, "b": 2}, is_optional=True)

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", json={"c": 3, "b": 2, "a": 1})
        assert (
            str(exception_info.value)
            == """No response can be found for POST request on https://test_url with b'{"c":3,"b":2,"a":1}' body amongst:
- Match any request with {'a': 1, 'b': 2} json body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_headers_and_json_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_json={"a": 1, "b": 2},
        match_headers={"foo": "bar"},
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", json={"c": 3, "b": 2, "a": 1})
        assert (
            str(exception_info.value)
            == """No response can be found for POST request on https://test_url with {} headers and b'{"c":3,"b":2,"a":1}' body amongst:
- Match any request with {'foo': 'bar'} headers and {'a': 1, 'b': 2} json body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_match_json_invalid_json(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_json={"a": 1, "b": 2}, is_optional=True)

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"<test>foobar</test>")
        assert (
            str(exception_info.value)
            == """No response can be found for POST request on https://test_url with b'<test>foobar</test>' body amongst:
- Match any request with {'a': 1, 'b': 2} json body"""
        )


@pytest.mark.asyncio
async def test_headers_and_content_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={"User-Agent": f"python-httpx/{httpx.__version__}"},
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url", content=b"This is the body")
        assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_headers_not_matching_and_content_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match any request with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_headers_matching_and_content_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match any request with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_headers_and_content_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match any request with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
async def test_url_and_headers_and_content_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={"User-Agent": f"python-httpx/{httpx.__version__}"},
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url", content=b"This is the body")
        assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_headers_not_matching_and_url_and_content_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match any request on https://test_url with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_url_and_headers_not_matching_and_content_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match any request on https://test_url2 with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_url_and_headers_matching_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match any request on https://test_url with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_headers_matching_and_url_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match any request on https://test_url2 with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_url_matching_and_headers_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match any request on https://test_url with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_url_and_headers_and_content_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match any request on https://test_url2 with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
async def test_method_and_url_and_headers_and_content_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={"User-Agent": f"python-httpx/{httpx.__version__}"},
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url", content=b"This is the body")
        assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_headers_not_matching_and_method_and_url_and_content_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match POST request on https://test_url with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_url_and_headers_not_matching_and_method_and_content_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        method="POST",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match POST request on https://test_url2 with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_method_and_url_and_headers_matching_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match POST request on https://test_url with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_method_and_headers_matching_and_url_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        method="POST",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match POST request on https://test_url2 with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_method_and_url_matching_and_headers_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match POST request on https://test_url with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_method_matching_and_url_and_headers_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        method="POST",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match POST request on https://test_url2 with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_method_and_url_and_headers_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        method="PUT",
        match_headers={
            "User-Agent": f"python-httpx/{httpx.__version__}",
            "Host": "test_url2",
        },
        match_content=b"This is the body2",
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'Host': 'test_url', 'User-Agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
- Match PUT request on https://test_url2 with {{'User-Agent': 'python-httpx/{httpx.__version__}', 'Host': 'test_url2'}} headers and b'This is the body2' body"""
        )


@pytest.mark.asyncio
async def test_header_as_str_tuple_list(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        headers=[("set-cookie", "key=value"), ("set-cookie", "key2=value2")]
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")

    assert dict(response.cookies) == {"key": "value", "key2": "value2"}


@pytest.mark.asyncio
async def test_header_as_bytes_tuple_list(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        headers=[(b"set-cookie", b"key=value"), (b"set-cookie", b"key2=value2")]
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")

    assert dict(response.cookies) == {"key": "value", "key2": "value2"}


@pytest.mark.asyncio
async def test_header_as_bytes_dict(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(headers={b"set-cookie": b"key=value"})

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")

    assert dict(response.cookies) == {"key": "value"}


@pytest.mark.asyncio
async def test_header_as_httpx_headers(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(headers=httpx.Headers({"set-cookie": "key=value"}))

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")

    assert dict(response.cookies) == {"key": "value"}


@pytest.mark.asyncio
async def test_elapsed_when_add_response(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
    assert response.elapsed is not None


@pytest.mark.asyncio
async def test_elapsed_when_add_callback(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_callback(
        callback=lambda req: httpx.Response(status_code=200, json={"foo": "bar"})
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
    assert response.elapsed is not None


@pytest.mark.asyncio
async def test_elapsed_when_add_async_callback(httpx_mock: HTTPXMock) -> None:
    async def custom_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"foo": "bar"})

    httpx_mock.add_callback(custom_response)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
    assert response.elapsed is not None


@pytest.mark.asyncio
async def test_non_ascii_url_response(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url?query_type=数据")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url?query_type=数据")
    assert response.content == b""


@pytest.mark.asyncio
async def test_url_encoded_matching_response(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url?a=%E6%95%B0%E6%8D%AE")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url?a=数据")
    assert response.content == b""


@pytest.mark.asyncio
async def test_reset_is_removing_requests(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response()
    async with httpx.AsyncClient() as client:
        await client.get("https://test_url")

    assert len(httpx_mock.get_requests()) == 1

    httpx_mock.reset()
    assert len(httpx_mock.get_requests()) == 0


@pytest.mark.asyncio
async def test_mutating_json(httpx_mock: HTTPXMock) -> None:
    mutating_json = {"content": "request 1"}
    httpx_mock.add_response(json=mutating_json)

    mutating_json["content"] = "request 2"
    httpx_mock.add_response(json=mutating_json)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.json() == {"content": "request 1"}

        response = await client.get("https://test_url")
        assert response.json() == {"content": "request 2"}


@pytest.mark.asyncio
async def test_streams_are_not_cascading_resulting_in_maximum_recursion(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(json={"abc": "def"}, is_reusable=True)
    async with httpx.AsyncClient() as client:
        tasks = [client.get("https://test_url") for _ in range(950)]
        await asyncio.gather(*tasks)
    # No need to assert anything, this test case ensure that no error was raised by the gather


@pytest.mark.asyncio
async def test_custom_transport(httpx_mock: HTTPXMock) -> None:
    class CustomTransport(httpx.AsyncHTTPTransport):
        def __init__(self, prefix: str, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.prefix = prefix

        async def handle_async_request(
            self,
            request: httpx.Request,
        ) -> httpx.Response:
            httpx_response = await super().handle_async_request(request)
            httpx_response.headers["x-prefix"] = self.prefix
            return httpx_response

    httpx_mock.add_response()

    async with httpx.AsyncClient(transport=CustomTransport(prefix="test")) as client:
        response = await client.post("https://test_url", content=b"This is the body")
        assert response.read() == b""
        assert response.headers["x-prefix"] == "test"


@pytest.mark.asyncio
async def test_response_selection_content_matching_with_async_iterable(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(match_content=b"full content 1", content=b"matched 1")
    httpx_mock.add_response(match_content=b"full content 2", content=b"matched 2")

    async def stream_content_1() -> AsyncIterable[bytes]:
        yield b"full"
        yield b" "
        yield b"content"
        yield b" 1"

    async def stream_content_2() -> AsyncIterable[bytes]:
        yield b"full"
        yield b" "
        yield b"content"
        yield b" 2"

    async with httpx.AsyncClient() as client:
        response_2 = await client.put("https://test_url", content=stream_content_2())
        response_1 = await client.put("https://test_url", content=stream_content_1())
    assert response_1.content == b"matched 1"
    assert response_2.content == b"matched 2"


@pytest.mark.asyncio
async def test_request_selection_content_matching_with_async_iterable(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(match_content=b"full content 1")
    httpx_mock.add_response(match_content=b"full content 2")

    async def stream_content_1() -> AsyncIterable[bytes]:
        yield b"full"
        yield b" "
        yield b"content"
        yield b" 1"

    async def stream_content_2() -> AsyncIterable[bytes]:
        yield b"full"
        yield b" "
        yield b"content"
        yield b" 2"

    async with httpx.AsyncClient() as client:
        await client.put("https://test_url_2", content=stream_content_2())
        await client.put("https://test_url_1", content=stream_content_1())
    assert (
        httpx_mock.get_request(match_content=b"full content 1").url
        == "https://test_url_1"
    )
    assert (
        httpx_mock.get_request(match_content=b"full content 2").url
        == "https://test_url_2"
    )


@pytest.mark.asyncio
async def test_files_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_files={"name": ("file_name", b"File content")})

    async with httpx.AsyncClient() as client:
        response = await client.put(
            "https://test_url", files={"name": ("file_name", b"File content")}
        )
    assert response.content == b""


@pytest.mark.asyncio
async def test_files_and_data_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_files={"name": ("file_name", b"File content")},
        match_data={"field": "value"},
    )

    async with httpx.AsyncClient() as client:
        response = await client.put(
            "https://test_url",
            files={"name": ("file_name", b"File content")},
            data={"field": "value"},
        )
    assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_files_not_matching_name(httpx_mock: HTTPXMock, monkeypatch) -> None:
    # Ensure generated boundary will be fbe495efe4cd41b941ca13e254d6b018
    monkeypatch.setattr(
        os,
        "urandom",
        lambda length: b"\xfb\xe4\x95\xef\xe4\xcdA\xb9A\xca\x13\xe2T\xd6\xb0\x18",
    )

    httpx_mock.add_response(
        match_files={"name2": ("file_name", b"File content")}, is_optional=True
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.put(
                "https://test_url", files={"name1": ("file_name", b"File content")}
            )
        assert (
            str(exception_info.value)
            == """No response can be found for PUT request on https://test_url with b'--fbe495efe4cd41b941ca13e254d6b018\\r\\nContent-Disposition: form-data; name="name1"; filename="file_name"\\r\\nContent-Type: application/octet-stream\\r\\n\\r\\nFile content\\r\\n--fbe495efe4cd41b941ca13e254d6b018--\\r\\n' body amongst:
- Match any request with {'name2': ('file_name', b'File content')} files"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_files_not_matching_file_name(httpx_mock: HTTPXMock, monkeypatch) -> None:
    # Ensure generated boundary will be fbe495efe4cd41b941ca13e254d6b018
    monkeypatch.setattr(
        os,
        "urandom",
        lambda length: b"\xfb\xe4\x95\xef\xe4\xcdA\xb9A\xca\x13\xe2T\xd6\xb0\x18",
    )

    httpx_mock.add_response(
        match_files={"name": ("file_name2", b"File content")}, is_optional=True
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.put(
                "https://test_url", files={"name": ("file_name1", b"File content")}
            )
        assert (
            str(exception_info.value)
            == """No response can be found for PUT request on https://test_url with b'--fbe495efe4cd41b941ca13e254d6b018\\r\\nContent-Disposition: form-data; name="name"; filename="file_name1"\\r\\nContent-Type: application/octet-stream\\r\\n\\r\\nFile content\\r\\n--fbe495efe4cd41b941ca13e254d6b018--\\r\\n' body amongst:
- Match any request with {'name': ('file_name2', b'File content')} files"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_files_not_matching_content(httpx_mock: HTTPXMock, monkeypatch) -> None:
    # Ensure generated boundary will be fbe495efe4cd41b941ca13e254d6b018
    monkeypatch.setattr(
        os,
        "urandom",
        lambda length: b"\xfb\xe4\x95\xef\xe4\xcdA\xb9A\xca\x13\xe2T\xd6\xb0\x18",
    )

    httpx_mock.add_response(
        match_files={"name": ("file_name", b"File content2")}, is_optional=True
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.put(
                "https://test_url", files={"name": ("file_name", b"File content1")}
            )
        assert (
            str(exception_info.value)
            == """No response can be found for PUT request on https://test_url with b'--fbe495efe4cd41b941ca13e254d6b018\\r\\nContent-Disposition: form-data; name="name"; filename="file_name"\\r\\nContent-Type: application/octet-stream\\r\\n\\r\\nFile content1\\r\\n--fbe495efe4cd41b941ca13e254d6b018--\\r\\n' body amongst:
- Match any request with {'name': ('file_name', b'File content2')} files"""
        )


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_files_matching_but_data_not_matching(
    httpx_mock: HTTPXMock, monkeypatch
) -> None:
    # Ensure generated boundary will be fbe495efe4cd41b941ca13e254d6b018
    monkeypatch.setattr(
        os,
        "urandom",
        lambda length: b"\xfb\xe4\x95\xef\xe4\xcdA\xb9A\xca\x13\xe2T\xd6\xb0\x18",
    )

    httpx_mock.add_response(
        match_files={"name": ("file_name", b"File content")},
        match_data={"field": "value"},
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.put(
                "https://test_url", files={"name": ("file_name", b"File content")}
            )
        assert (
            str(exception_info.value)
            == """No response can be found for PUT request on https://test_url with b'--fbe495efe4cd41b941ca13e254d6b018\\r\\nContent-Disposition: form-data; name="name"; filename="file_name"\\r\\nContent-Type: application/octet-stream\\r\\n\\r\\nFile content\\r\\n--fbe495efe4cd41b941ca13e254d6b018--\\r\\n' body amongst:
- Match any request with {'field': 'value'} multipart data and {'name': ('file_name', b'File content')} files"""
        )


@pytest.mark.asyncio
async def test_timeout_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_extensions={"timeout": {"connect": 5, "read": 5, "write": 10, "pool": 5}}
    )

    async with httpx.AsyncClient() as client:
        response = await client.put(
            "https://test_url", timeout=httpx.Timeout(5, write=10)
        )
    assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_timeout_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_extensions={"timeout": {"connect": 5, "read": 5, "write": 10, "pool": 5}},
        is_optional=True,
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get("https://test_url", extensions={"test": "value"})
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url with {'timeout': {'connect': 5.0, 'read': 5.0, 'write': 5.0, 'pool': 5.0}} extensions amongst:
- Match any request with {'timeout': {'connect': 5, 'read': 5, 'write': 10, 'pool': 5}} extensions"""
        )


@pytest.mark.asyncio
async def test_extensions_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_extensions={"test": "value"})

    async with httpx.AsyncClient() as client:
        response = await client.put(
            "https://test_url", extensions={"test": "value", "test2": "value2"}
        )
    assert response.content == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
async def test_extensions_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_extensions={"test": "value"}, is_optional=True)

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get("https://test_url", extensions={"test": "value2"})
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url with {'test': 'value2'} extensions amongst:
- Match any request with {'test': 'value'} extensions"""
        )


@pytest.mark.asyncio
async def test_optional_response_not_matched(httpx_mock: HTTPXMock) -> None:
    # This response is optional and the fact that it was never requested should not trigger anything
    httpx_mock.add_response(url="https://test_url", is_optional=True)
    httpx_mock.add_response(url="https://test_url2")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url2")
    assert response.content == b""


@pytest.mark.asyncio
async def test_optional_response_matched(httpx_mock: HTTPXMock) -> None:
    # This response is optional and the fact that it was never requested should not trigger anything
    httpx_mock.add_response(url="https://test_url", is_optional=True)
    httpx_mock.add_response(url="https://test_url2")

    async with httpx.AsyncClient() as client:
        response1 = await client.get("https://test_url")
        response2 = await client.get("https://test_url2")
    assert response1.content == b""
    assert response2.content == b""


@pytest.mark.asyncio
@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
async def test_mandatory_response_matched(httpx_mock: HTTPXMock) -> None:
    # This response is optional and the fact that it was never requested should not trigger anything
    httpx_mock.add_response(url="https://test_url")
    # This response MUST be requested (overrides global settings via marker)
    httpx_mock.add_response(url="https://test_url2", is_optional=False)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url2")
    assert response.content == b""


@pytest.mark.asyncio
async def test_multi_response_matched_once(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", is_reusable=True)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
    assert response.content == b""


@pytest.mark.asyncio
async def test_multi_response_matched_twice(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", is_reusable=True)

    async with httpx.AsyncClient() as client:
        response1 = await client.get("https://test_url")
        response2 = await client.get("https://test_url")
    assert response1.content == b""
    assert response2.content == b""
