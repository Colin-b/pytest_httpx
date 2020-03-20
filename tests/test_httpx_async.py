import re
from typing import Optional

import pytest
import httpx
from httpx._content_streams import JSONStream

from pytest_httpx import httpx_mock, HTTPXMock


@pytest.mark.asyncio
async def test_without_response(httpx_mock: HTTPXMock):
    with pytest.raises(Exception) as exception_info:
        async with httpx.AsyncClient() as client:
            await client.get("http://test_url")
    assert (
        str(exception_info.value)
        == "No mock can be found for GET request on http://test_url."
    )


@pytest.mark.asyncio
async def test_default_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
    assert response.content == b""
    assert response.status_code == 200
    assert response.headers == httpx.Headers({})
    assert response.http_version == "HTTP/1.1"


@pytest.mark.asyncio
async def test_url_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test_url")

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.content == b""

        response = await client.post("http://test_url")
        assert response.content == b""


@pytest.mark.asyncio
async def test_method_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="get")

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.content == b""

        response = await client.get("http://test_url2")
        assert response.content == b""


@pytest.mark.asyncio
async def test_with_one_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test_url", data=b"test content")

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.content == b"test content"

        response = await client.get("http://test_url")
        assert response.content == b"test content"


@pytest.mark.asyncio
async def test_with_many_responses(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test_url", data=b"test content 1")
    httpx_mock.add_response(url="http://test_url", data=b"test content 2")

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.content == b"test content 1"

        response = await client.get("http://test_url")
        assert response.content == b"test content 2"

        response = await client.get("http://test_url")
        assert response.content == b"test content 2"


@pytest.mark.asyncio
async def test_with_many_responses_methods(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test_url", method="GET", data=b"test content 1")
    httpx_mock.add_response(
        url="http://test_url", method="POST", data=b"test content 2"
    )
    httpx_mock.add_response(url="http://test_url", method="PUT", data=b"test content 3")
    httpx_mock.add_response(
        url="http://test_url", method="DELETE", data=b"test content 4"
    )
    httpx_mock.add_response(
        url="http://test_url", method="PATCH", data=b"test content 5"
    )
    httpx_mock.add_response(
        url="http://test_url", method="HEAD", data=b"test content 6"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("http://test_url")
        assert response.content == b"test content 2"

        response = await client.get("http://test_url")
        assert response.content == b"test content 1"

        response = await client.put("http://test_url")
        assert response.content == b"test content 3"

        response = await client.head("http://test_url")
        assert response.content == b"test content 6"

        response = await client.patch("http://test_url")
        assert response.content == b"test content 5"

        response = await client.delete("http://test_url")
        assert response.content == b"test content 4"


@pytest.mark.asyncio
async def test_with_many_responses_status_codes(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://test_url", method="GET", data=b"test content 1", status_code=200
    )
    httpx_mock.add_response(
        url="http://test_url", method="POST", data=b"test content 2", status_code=201
    )
    httpx_mock.add_response(
        url="http://test_url", method="PUT", data=b"test content 3", status_code=202
    )
    httpx_mock.add_response(
        url="http://test_url", method="DELETE", data=b"test content 4", status_code=303
    )
    httpx_mock.add_response(
        url="http://test_url", method="PATCH", data=b"test content 5", status_code=404
    )
    httpx_mock.add_response(
        url="http://test_url", method="HEAD", data=b"test content 6", status_code=500
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("http://test_url")
        assert response.content == b"test content 2"
        assert response.status_code == 201

        response = await client.get("http://test_url")
        assert response.content == b"test content 1"
        assert response.status_code == 200

        response = await client.put("http://test_url")
        assert response.content == b"test content 3"
        assert response.status_code == 202

        response = await client.head("http://test_url")
        assert response.content == b"test content 6"
        assert response.status_code == 500

        response = await client.patch("http://test_url")
        assert response.content == b"test content 5"
        assert response.status_code == 404

        response = await client.delete("http://test_url")
        assert response.content == b"test content 4"
        assert response.status_code == 303


@pytest.mark.asyncio
async def test_with_many_responses_urls_str(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://test_url?param1=test", method="GET", data=b"test content 1"
    )
    httpx_mock.add_response(
        url="http://test_url?param2=test", method="POST", data=b"test content 2"
    )
    httpx_mock.add_response(
        url="http://test_url?param3=test", method="PUT", data=b"test content 3"
    )
    httpx_mock.add_response(
        url="http://test_url?param4=test", method="DELETE", data=b"test content 4"
    )
    httpx_mock.add_response(
        url="http://test_url?param5=test", method="PATCH", data=b"test content 5"
    )
    httpx_mock.add_response(
        url="http://test_url?param6=test", method="HEAD", data=b"test content 6"
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            httpx.URL("http://test_url", params={"param2": "test"})
        )
        assert response.content == b"test content 2"

        response = await client.get(
            httpx.URL("http://test_url", params={"param1": "test"})
        )
        assert response.content == b"test content 1"

        response = await client.put(
            httpx.URL("http://test_url", params={"param3": "test"})
        )
        assert response.content == b"test content 3"

        response = await client.head(
            httpx.URL("http://test_url", params={"param6": "test"})
        )
        assert response.content == b"test content 6"

        response = await client.patch(
            httpx.URL("http://test_url", params={"param5": "test"})
        )
        assert response.content == b"test content 5"

        response = await client.delete(
            httpx.URL("http://test_url", params={"param4": "test"})
        )
        assert response.content == b"test content 4"


@pytest.mark.asyncio
async def test_response_with_pattern_in_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=re.compile(".*test.*"))
    httpx_mock.add_response(url="http://unmatched", data=b"test content")

    async with httpx.AsyncClient() as client:
        response = await client.get("http://unmatched")
        assert response.content == b"test content"

        response = await client.get("http://test_url")
        assert response.content == b""


@pytest.mark.asyncio
async def test_request_with_pattern_in_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test_url")
    httpx_mock.add_response(url="http://unmatched")

    async with httpx.AsyncClient() as client:
        await client.get("http://unmatched")
        await client.get("http://test_url", headers={"X-Test": "1"})

    assert httpx_mock.get_request(url=re.compile(".*test.*")).headers["x-test"] == "1"


@pytest.mark.asyncio
async def test_requests_with_pattern_in_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test_url")
    httpx_mock.add_response(url="http://tests_url")
    httpx_mock.add_response(url="http://unmatched")

    async with httpx.AsyncClient() as client:
        await client.get("http://tests_url", headers={"X-Test": "1"})
        await client.get("http://unmatched", headers={"X-Test": "2"})
        await client.get("http://test_url")

    requests = httpx_mock.get_requests(url=re.compile(".*test.*"))
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "1"
    assert "x-test" not in requests[1].headers


@pytest.mark.asyncio
async def test_callback_with_pattern_in_url(httpx_mock: HTTPXMock):
    def custom_response(
        request: httpx.Request, timeout: Optional[httpx.Timeout], *args, **kwargs
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            http_version="HTTP/1.1",
            headers=[],
            stream=JSONStream({"url": str(request.url)}),
            request=request,
        )

    def custom_response2(
        request: httpx.Request, timeout: Optional[httpx.Timeout], *args, **kwargs
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            http_version="HTTP/2.0",
            headers=[],
            stream=JSONStream({"url": str(request.url)}),
            request=request,
        )

    httpx_mock.add_callback(custom_response, url=re.compile(".*test.*"))
    httpx_mock.add_callback(custom_response2, url="http://unmatched")

    async with httpx.AsyncClient() as client:
        response = await client.get("http://unmatched")
        assert response.http_version == "HTTP/2.0"

        response = await client.get("http://test_url")
        assert response.http_version == "HTTP/1.1"


@pytest.mark.asyncio
async def test_with_many_responses_urls_instances(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=httpx.URL("http://test_url", params={"param1": "test"}),
        method="GET",
        data=b"test content 1",
    )
    httpx_mock.add_response(
        url=httpx.URL("http://test_url", params={"param2": "test"}),
        method="POST",
        data=b"test content 2",
    )
    httpx_mock.add_response(
        url=httpx.URL("http://test_url", params={"param3": "test"}),
        method="PUT",
        data=b"test content 3",
    )
    httpx_mock.add_response(
        url=httpx.URL("http://test_url", params={"param4": "test"}),
        method="DELETE",
        data=b"test content 4",
    )
    httpx_mock.add_response(
        url=httpx.URL("http://test_url", params={"param5": "test"}),
        method="PATCH",
        data=b"test content 5",
    )
    httpx_mock.add_response(
        url=httpx.URL("http://test_url", params={"param6": "test"}),
        method="HEAD",
        data=b"test content 6",
    )

    async with httpx.AsyncClient() as client:
        response = await client.post("http://test_url?param2=test")
        assert response.content == b"test content 2"

        response = await client.get("http://test_url?param1=test")
        assert response.content == b"test content 1"

        response = await client.put("http://test_url?param3=test")
        assert response.content == b"test content 3"

        response = await client.head("http://test_url?param6=test")
        assert response.content == b"test content 6"

        response = await client.patch("http://test_url?param5=test")
        assert response.content == b"test content 5"

        response = await client.delete("http://test_url?param4=test")
        assert response.content == b"test content 4"


@pytest.mark.asyncio
async def test_with_http_version_2(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://test_url", http_version="HTTP/2", data=b"test content 1"
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.content == b"test content 1"
        assert response.http_version == "HTTP/2"


@pytest.mark.asyncio
async def test_with_headers(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://test_url", data=b"test content 1", headers={"X-Test": "Test value"}
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.content == b"test content 1"
        assert response.headers == httpx.Headers({"x-test": "Test value"})


@pytest.mark.asyncio
async def test_multipart_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test_url", data={"key1": "value1"})
    httpx_mock.add_response(
        url="http://test_url",
        files={"file1": "content of file 1"},
        boundary=b"2256d3a36d2a61a1eba35a22bee5c74a",
    )
    httpx_mock.add_response(
        url="http://test_url",
        data={"key1": "value1"},
        files={"file1": "content of file 1"},
        boundary=b"2256d3a36d2a61a1eba35a22bee5c74a",
    )

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.text == "key1=value1"

        response = await client.get("http://test_url")
        assert (
            response.text
            == '--2256d3a36d2a61a1eba35a22bee5c74a\r\nContent-Disposition: form-data; name="file1"; filename="upload"\r\nContent-Type: application/octet-stream\r\n\r\ncontent of file 1\r\n--2256d3a36d2a61a1eba35a22bee5c74a--\r\n'
        )

        response = await client.get("http://test_url")
        assert (
            response.text
            == """--2256d3a36d2a61a1eba35a22bee5c74a\r
Content-Disposition: form-data; name="key1"\r
\r
value1\r
--2256d3a36d2a61a1eba35a22bee5c74a\r
Content-Disposition: form-data; name="file1"; filename="upload"\r
Content-Type: application/octet-stream\r
\r
content of file 1\r
--2256d3a36d2a61a1eba35a22bee5c74a--\r
"""
        )


@pytest.mark.asyncio
async def test_requests_retrieval(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test_url", method="GET", data=b"test content 1")
    httpx_mock.add_response(
        url="http://test_url", method="POST", data=b"test content 2"
    )
    httpx_mock.add_response(url="http://test_url", method="PUT", data=b"test content 3")
    httpx_mock.add_response(
        url="http://test_url", method="DELETE", data=b"test content 4"
    )
    httpx_mock.add_response(
        url="http://test_url", method="PATCH", data=b"test content 5"
    )
    httpx_mock.add_response(
        url="http://test_url", method="HEAD", data=b"test content 6"
    )

    async with httpx.AsyncClient() as client:
        await client.post("http://test_url", data=b"sent content 2")
        await client.get("http://test_url", headers={"X-TEST": "test header 1"})
        await client.put("http://test_url", data=b"sent content 3")
        await client.head("http://test_url")
        await client.patch("http://test_url", data=b"sent content 5")
        await client.delete("http://test_url", headers={"X-Test": "test header 4"})

    assert (
        httpx_mock.get_request(url=httpx.URL("http://test_url"), method="PATCH").read()
        == b"sent content 5"
    )
    assert (
        httpx_mock.get_request(url=httpx.URL("http://test_url"), method="HEAD").read()
        == b""
    )
    assert (
        httpx_mock.get_request(url=httpx.URL("http://test_url"), method="PUT").read()
        == b"sent content 3"
    )
    assert (
        httpx_mock.get_request(url=httpx.URL("http://test_url"), method="GET").headers[
            "x-test"
        ]
        == "test header 1"
    )
    assert (
        httpx_mock.get_request(url=httpx.URL("http://test_url"), method="POST").read()
        == b"sent content 2"
    )
    assert (
        httpx_mock.get_request(
            url=httpx.URL("http://test_url"), method="DELETE"
        ).headers["x-test"]
        == "test header 4"
    )


@pytest.mark.asyncio
async def test_requests_retrieval_on_same_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="http://test_url")

    async with httpx.AsyncClient() as client:
        await client.get("http://test_url", headers={"X-TEST": "test header 1"})
        await client.get("http://test_url", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests(url=httpx.URL("http://test_url"))
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


@pytest.mark.asyncio
async def test_request_retrieval_on_same_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.get("http://test_url", headers={"X-TEST": "test header 1"})
        await client.get("http://test_url2", headers={"X-TEST": "test header 2"})

    request = httpx_mock.get_request(url=httpx.URL("http://test_url"))
    assert request.headers["x-test"] == "test header 1"


@pytest.mark.asyncio
async def test_requests_retrieval_on_same_method(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.get("http://test_url", headers={"X-TEST": "test header 1"})
        await client.get("http://test_url2", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests(method="GET")
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


@pytest.mark.asyncio
async def test_request_retrieval_on_same_method(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.get("http://test_url", headers={"X-TEST": "test header 1"})
        await client.post("http://test_url", headers={"X-TEST": "test header 2"})

    request = httpx_mock.get_request(method="GET")
    assert request.headers["x-test"] == "test header 1"


@pytest.mark.asyncio
async def test_requests_retrieval_on_same_url_and_method(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.get("http://test_url", headers={"X-TEST": "test header 1"})
        await client.get("http://test_url", headers={"X-TEST": "test header 2"})
        await client.post("http://test_url", headers={"X-TEST": "test header 3"})
        await client.get("http://test_url2", headers={"X-TEST": "test header 4"})

    requests = httpx_mock.get_requests(url=httpx.URL("http://test_url"), method="GET")
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


@pytest.mark.asyncio
async def test_default_requests_retrieval(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.post("http://test_url", headers={"X-TEST": "test header 1"})
        await client.get("http://test_url2", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


@pytest.mark.asyncio
async def test_default_request_retrieval(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.post("http://test_url", headers={"X-TEST": "test header 1"})

    request = httpx_mock.get_request()
    assert request.headers["x-test"] == "test header 1"


@pytest.mark.asyncio
async def test_requests_json_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://test_url", method="GET", json=["list content 1", "list content 2"]
    )
    httpx_mock.add_response(
        url="http://test_url",
        method="POST",
        json={"key 1": "value 1", "key 2": "value 2"},
    )
    httpx_mock.add_response(url="http://test_url", method="PUT", json="string value")

    async with httpx.AsyncClient() as client:
        response = await client.post("http://test_url")
        assert response.json() == {"key 1": "value 1", "key 2": "value 2"}

        response = await client.get("http://test_url")
        assert response.json() == ["list content 1", "list content 2"]

        response = await client.put("http://test_url")
        assert response.json() == "string value"


@pytest.mark.asyncio
async def test_callback_raising_exception(httpx_mock: HTTPXMock):
    def raise_timeout(
        request: httpx.Request, timeout: Optional[httpx.Timeout], *args, **kwargs
    ) -> httpx.Response:
        raise httpx.TimeoutException()

    httpx_mock.add_callback(raise_timeout, url="http://test_url")

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.TimeoutException):
            await client.get("http://test_url")


@pytest.mark.asyncio
async def test_callback_returning_response(httpx_mock: HTTPXMock):
    def custom_response(
        request: httpx.Request, timeout: Optional[httpx.Timeout], *args, **kwargs
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            http_version="HTTP/1.1",
            headers=[],
            stream=JSONStream({"url": str(request.url)}),
            request=request,
        )

    httpx_mock.add_callback(custom_response, url="http://test_url")

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.json() == {"url": "http://test_url"}


@pytest.mark.asyncio
async def test_callback_executed_twice(httpx_mock: HTTPXMock):
    def custom_response(
        request: httpx.Request, timeout: Optional[httpx.Timeout], *args, **kwargs
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            http_version="HTTP/1.1",
            headers=[],
            stream=JSONStream(["content"]),
            request=request,
        )

    httpx_mock.add_callback(custom_response)

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.json() == ["content"]

        response = await client.post("http://test_url")
        assert response.json() == ["content"]


@pytest.mark.asyncio
async def test_callback_matching_method(httpx_mock: HTTPXMock):
    def custom_response(
        request: httpx.Request, timeout: Optional[httpx.Timeout], *args, **kwargs
    ) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            http_version="HTTP/1.1",
            headers=[],
            stream=JSONStream(["content"]),
            request=request,
        )

    httpx_mock.add_callback(custom_response, method="GET")

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.json() == ["content"]

        response = await client.get("http://test_url2")
        assert response.json() == ["content"]


@pytest.mark.xfail(
    raises=AssertionError,
    reason="Single request cannot be returned if there is more than one matching.",
)
@pytest.mark.asyncio
async def test_request_retrieval_with_more_than_one(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        await client.get("http://test_url", headers={"X-TEST": "test header 1"})
        await client.get("http://test_url", headers={"X-TEST": "test header 2"})

    httpx_mock.get_request(url=httpx.URL("http://test_url"))


@pytest.mark.asyncio
async def test_headers_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_headers={"user-agent": "python-httpx/0.12.1"})

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
        assert response.content == b""


@pytest.mark.asyncio
async def test_headers_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        match_headers={
            "user-agent": "python-httpx/0.12.0",
            "host": "test_url2",
            "host2": "test_url",
        }
    )

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPError) as exception_info:
            await client.get("http://test_url")
        assert (
            str(exception_info.value)
            == "No mock can be found for GET request on http://test_url."
        )

    # Clean up responses to avoid assertion failure
    httpx_mock._responses.clear()


@pytest.mark.asyncio
async def test_content_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_content=b"This is the body")

    async with httpx.AsyncClient() as client:
        response = await client.post("http://test_url", data=b"This is the body")
        assert response.read() == b""


@pytest.mark.asyncio
async def test_content_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_content=b"This is the body")

    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.HTTPError) as exception_info:
            await client.post("http://test_url", data=b"This is the body2")
        assert (
            str(exception_info.value)
            == "No mock can be found for POST request on http://test_url."
        )

    # Clean up responses to avoid assertion failure
    httpx_mock._responses.clear()
