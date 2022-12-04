import asyncio
import math
import re
import time

import httpx
import pytest
from pytest import Testdir

import pytest_httpx
from pytest_httpx import HTTPXMock


@pytest.mark.asyncio
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

        response = await client.post("https://test_url")
        assert response.content == b""


@pytest.mark.asyncio
async def test_url_query_string_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url?a=1&b=2")

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url?a=1&b=2")
        assert response.content == b""

        # Parameters order should not matter
        response = await client.get("https://test_url?b=2&a=1")
        assert response.content == b""


@pytest.mark.asyncio
async def test_url_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url")

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get("https://test_url2")
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url2 amongst:
Match all requests on https://test_url"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_url_query_string_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url?a=1&a=2")

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            # Same parameter order matters as it corresponds to a list on server side
            await client.get("https://test_url?a=2&a=1")
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url?a=2&a=1 amongst:
Match all requests on https://test_url?a=1&a=2"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_method_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="get")

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b""

        response = await client.get("https://test_url2")
        assert response.content == b""


@pytest.mark.asyncio
async def test_method_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(method="get")

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url")
        assert (
            str(exception_info.value)
            == """No response can be found for POST request on https://test_url amongst:
Match GET requests"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_with_one_response(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", content=b"test content")

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
    )

    async with httpx.AsyncClient() as client:
        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1",
                b"part 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for part in response.aiter_raw():
                    pass  # pragma: no cover

        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1",
                b"part 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for part in response.aiter_raw():
                    pass  # pragma: no cover


@pytest.mark.asyncio
async def test_content_response_streaming(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        content=b"part 1 and 2",
    )

    async with httpx.AsyncClient() as client:
        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1 and 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for part in response.aiter_raw():
                    pass  # pragma: no cover

        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1 and 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for part in response.aiter_raw():
                    pass  # pragma: no cover


@pytest.mark.asyncio
async def test_text_response_streaming(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        text="part 1 and 2",
    )

    async with httpx.AsyncClient() as client:
        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1 and 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for part in response.aiter_raw():
                    pass  # pragma: no cover

        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [
                b"part 1 and 2",
            ]
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for part in response.aiter_raw():
                    pass  # pragma: no cover


@pytest.mark.asyncio
async def test_default_response_streaming(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == []
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for part in response.aiter_raw():
                    pass  # pragma: no cover

        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == []
            # Assert that stream still behaves the proper way (can only be consumed once per request)
            with pytest.raises(httpx.StreamConsumed):
                async for part in response.aiter_raw():
                    pass  # pragma: no cover


@pytest.mark.asyncio
async def test_with_many_responses(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", content=b"test content 1")
    httpx_mock.add_response(url="https://test_url", content=b"test content 2")

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
    httpx_mock.add_response(url="https://test_url")

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url", headers={"X-TEST": "test header 1"})
        await client.get("https://test_url", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests(url=httpx.URL("https://test_url"))
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


@pytest.mark.asyncio
async def test_request_retrieval_on_same_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url", headers={"X-TEST": "test header 1"})
        await client.get("https://test_url2", headers={"X-TEST": "test header 2"})

    request = httpx_mock.get_request(url=httpx.URL("https://test_url"))
    assert request.headers["x-test"] == "test header 1"


@pytest.mark.asyncio
async def test_requests_retrieval_on_same_method(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url", headers={"X-TEST": "test header 1"})
        await client.get("https://test_url2", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests(method="GET")
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


@pytest.mark.asyncio
async def test_request_retrieval_on_same_method(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.get("https://test_url", headers={"X-TEST": "test header 1"})
        await client.post("https://test_url", headers={"X-TEST": "test header 2"})

    request = httpx_mock.get_request(method="GET")
    assert request.headers["x-test"] == "test header 1"


@pytest.mark.asyncio
async def test_requests_retrieval_on_same_url_and_method(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response()

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
    httpx_mock.add_response()

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

    httpx_mock.add_callback(custom_response)

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

    httpx_mock.add_callback(custom_response)

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
    httpx_mock.add_callback(custom_response)

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
    httpx_mock.add_callback(custom_response)

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
    httpx_mock.add_response(json=["content2"])

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
    httpx_mock.add_response(json=["content2"])

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

    httpx_mock.add_callback(custom_response, method="GET")

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

    httpx_mock.add_callback(custom_response, method="GET")

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
        import pytest
        import httpx
        
        
        @pytest.mark.asyncio
        async def test_request_retrieval_with_more_than_one(httpx_mock):
            httpx_mock.add_response()
        
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
            "*AssertionError: More than one request (2) matched, use get_requests instead."
        ]
    )


@pytest.mark.asyncio
async def test_headers_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={"user-agent": f"python-httpx/{httpx.__version__}"}
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
        assert response.content == b""


@pytest.mark.asyncio
async def test_headers_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
            "host2": "test_url",
        }
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.get("https://test_url")
        assert (
            str(exception_info.value)
            == f"""No response can be found for GET request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers amongst:
Match all requests with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2', 'host2': 'test_url'}} headers"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_content_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_content=b"This is the body")

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url", content=b"This is the body")
        assert response.read() == b""


@pytest.mark.asyncio
async def test_content_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(match_content=b"This is the body")

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body2")
        assert (
            str(exception_info.value)
            == """No response can be found for POST request on https://test_url with b'This is the body2' body amongst:
Match all requests with b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_headers_and_content_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={"user-agent": f"python-httpx/{httpx.__version__}"},
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url", content=b"This is the body")
        assert response.content == b""


@pytest.mark.asyncio
async def test_headers_not_matching_and_content_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_headers_matching_and_content_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_headers_and_content_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_url_and_headers_and_content_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={"user-agent": f"python-httpx/{httpx.__version__}"},
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url", content=b"This is the body")
        assert response.content == b""


@pytest.mark.asyncio
async def test_headers_not_matching_and_url_and_content_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_url_and_headers_not_matching_and_content_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_url_and_headers_matching_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_headers_matching_and_url_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_url_matching_and_headers_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_url_and_headers_and_content_not_matching(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_method_and_url_and_headers_and_content_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={"user-agent": f"python-httpx/{httpx.__version__}"},
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("https://test_url", content=b"This is the body")
        assert response.content == b""


@pytest.mark.asyncio
async def test_headers_not_matching_and_method_and_url_and_content_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_url_and_headers_not_matching_and_method_and_content_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_method_and_url_and_headers_matching_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_method_and_headers_matching_and_url_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_method_and_url_matching_and_headers_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_method_matching_and_url_and_headers_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


@pytest.mark.asyncio
async def test_method_and_url_and_headers_and_content_not_matching(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://test_url2",
        method="PUT",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            await client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match PUT requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


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

    httpx_mock.reset(assert_all_responses_were_requested=False)
    assert len(httpx_mock.get_requests()) == 0


@pytest.mark.asyncio
async def test_response_with_pattern_in_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url", headers={"X-Test": "1"})
    httpx_mock.add_response(url="https://unmatched")

    async with httpx.AsyncClient() as client:
        await client.get("https://unmatched")
        await client.get("https://test_url")

    assert httpx_mock.get_response(url=re.compile(".*test.*")).headers["x-test"] == "1"


@pytest.mark.asyncio
async def test_responses_with_pattern_in_url(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(url="https://test_url")
    httpx_mock.add_response(url="https://tests_url", headers={"X-Test": "1"})
    httpx_mock.add_response(url="https://unmatched", headers={"X-Test": "2"})

    async with httpx.AsyncClient() as client:
        await client.get("https://tests_url")
        await client.get("https://unmatched")
        await client.get("https://test_url")

    responses = httpx_mock.get_responses(url=re.compile(".*test.*"))
    assert len(responses) == 2
    assert responses[0].headers["x-test"] == "1"
    assert "x-test" not in responses[1].headers


@pytest.mark.asyncio
async def test_responses_retrieval(httpx_mock: HTTPXMock) -> None:
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
        httpx_mock.get_response(
            url=httpx.URL("https://test_url"), method="PATCH"
        ).read()
        == b"test content 5"
    )
    assert (
        httpx_mock.get_response(url=httpx.URL("https://test_url"), method="HEAD").read()
        == b"test content 6"
    )
    assert (
        httpx_mock.get_response(url=httpx.URL("https://test_url"), method="PUT").read()
        == b"test content 3"
    )
    assert (
        httpx_mock.get_response(url=httpx.URL("https://test_url"), method="GET").read()
        == b"test content 1"
    )
    assert (
        httpx_mock.get_response(url=httpx.URL("https://test_url"), method="POST").read()
        == b"test content 2"
    )
    assert (
        httpx_mock.get_response(
            url=httpx.URL("https://test_url"), method="DELETE"
        ).read()
        == b"test content 4"
    )


@pytest.mark.asyncio
async def test_reset_is_removing_responses(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response()
    async with httpx.AsyncClient() as client:
        await client.get("https://test_url")

    assert len(httpx_mock.get_responses()) == 1

    httpx_mock.reset(assert_all_responses_were_requested=False)
    assert len(httpx_mock.get_responses()) == 0
