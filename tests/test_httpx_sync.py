import re

import httpx
import pytest

import pytest_httpx
from pytest_httpx import HTTPXMock


def test_without_response(httpx_mock: HTTPXMock):
    with pytest.raises(Exception) as exception_info:
        with httpx.Client() as client:
            client.get("https://test_url")
    assert (
        str(exception_info.value)
        == """No response can be found for GET request on https://test_url"""
    )


def test_default_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        response = client.get("https://test_url")
    assert response.content == b""
    assert response.status_code == 200
    assert response.headers == httpx.Headers({})
    assert response.http_version == "HTTP/1.1"


def test_url_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url")

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.content == b""

        response = client.post("https://test_url")
        assert response.content == b""


def test_url_query_string_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url?a=1&b=2")

    with httpx.Client() as client:
        response = client.post("https://test_url?a=1&b=2")
        assert response.content == b""

        # Parameters order should not matter
        response = client.get("https://test_url?b=2&a=1")
        assert response.content == b""


def test_url_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url")

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.get("https://test_url2")
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url2 amongst:
Match all requests on https://test_url"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_url_query_string_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url?a=1&a=2")

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            # Same parameter order matters as it corresponds to a list on server side
            client.get("https://test_url?a=2&a=1")
        assert (
            str(exception_info.value)
            == """No response can be found for GET request on https://test_url?a=2&a=1 amongst:
Match all requests on https://test_url?a=1&a=2"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_method_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="get")

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.content == b""

        response = client.get("https://test_url2")
        assert response.content == b""


def test_method_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="get")

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url")
        assert (
            str(exception_info.value)
            == """No response can be found for POST request on https://test_url amongst:
Match GET requests"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_with_one_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url", content=b"test content")

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.content == b"test content"

        response = client.get("https://test_url")
        assert response.content == b"test content"


def test_deprecated_response_with_bytes_body(httpx_mock: HTTPXMock):
    with pytest.warns(
        DeprecationWarning,
        match="data parameter as bytes will be removed in a future version. Use content parameter instead.",
    ):
        httpx_mock.add_response(url="https://test_url", data=b"test content")

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.content == b"test content"


def test_response_with_string_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url", text="test content")

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.content == b"test content"


def test_deprecated_response_with_string_body(httpx_mock: HTTPXMock):
    with pytest.warns(
        DeprecationWarning,
        match="data parameter as str will be removed in a future version. Use text parameter instead.",
    ):
        httpx_mock.add_response(url="https://test_url", data="test content")

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.content == b"test content"


def test_response_with_html_string_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url", html="<body>test content</body>")

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.text == "<body>test content</body>"


def test_response_streaming(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url",
        stream=pytest_httpx.IteratorStream([b"part 1", b"part 2"]),
    )

    with httpx.Client() as client:
        with client.stream(method="GET", url="https://test_url") as response:
            assert list(response.iter_raw()) == [b"part 1", b"part 2"]


def test_deprecated_response_streaming(httpx_mock: HTTPXMock):
    with pytest.warns(
        DeprecationWarning,
        match="data parameter as iterator will be removed in a future version. Use stream parameter instead.",
    ):
        httpx_mock.add_response(url="https://test_url", data=[b"part 1", b"part 2"])

    with httpx.Client() as client:
        with client.stream(method="GET", url="https://test_url") as response:
            assert list(response.iter_raw()) == [b"part 1", b"part 2"]


@pytest.mark.xfail
def test_with_many_responses(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url", content=b"test content 1")
    httpx_mock.add_response(url="https://test_url", content=b"test content 2")

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.content == b"test content 1"

        response = client.get("https://test_url")
        assert response.content == b"test content 2"

        response = client.get("https://test_url")
        assert response.content == b"test content 2"


def test_with_many_responses_methods(httpx_mock: HTTPXMock):
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

    with httpx.Client() as client:
        response = client.post("https://test_url")
        assert response.content == b"test content 2"

        response = client.get("https://test_url")
        assert response.content == b"test content 1"

        response = client.put("https://test_url")
        assert response.content == b"test content 3"

        response = client.head("https://test_url")
        assert response.content == b"test content 6"

        response = client.patch("https://test_url")
        assert response.content == b"test content 5"

        response = client.delete("https://test_url")
        assert response.content == b"test content 4"


def test_with_many_responses_status_codes(httpx_mock: HTTPXMock):
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

    with httpx.Client() as client:
        response = client.post("https://test_url")
        assert response.content == b"test content 2"
        assert response.status_code == 201

        response = client.get("https://test_url")
        assert response.content == b"test content 1"
        assert response.status_code == 200

        response = client.put("https://test_url")
        assert response.content == b"test content 3"
        assert response.status_code == 202

        response = client.head("https://test_url")
        assert response.content == b"test content 6"
        assert response.status_code == 500

        response = client.patch("https://test_url")
        assert response.content == b"test content 5"
        assert response.status_code == 404

        response = client.delete("https://test_url")
        assert response.content == b"test content 4"
        assert response.status_code == 303


def test_with_many_responses_urls_str(httpx_mock: HTTPXMock):
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

    with httpx.Client() as client:
        response = client.post(httpx.URL("https://test_url", params={"param2": "test"}))
        assert response.content == b"test content 2"

        response = client.get(httpx.URL("https://test_url", params={"param1": "test"}))
        assert response.content == b"test content 1"

        response = client.put(httpx.URL("https://test_url", params={"param3": "test"}))
        assert response.content == b"test content 3"

        response = client.head(httpx.URL("https://test_url", params={"param6": "test"}))
        assert response.content == b"test content 6"

        response = client.patch(
            httpx.URL("https://test_url", params={"param5": "test"})
        )
        assert response.content == b"test content 5"

        response = client.delete(
            httpx.URL("https://test_url", params={"param4": "test"})
        )
        assert response.content == b"test content 4"


def test_response_with_pattern_in_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=re.compile(".*test.*"))
    httpx_mock.add_response(url="https://unmatched", content=b"test content")

    with httpx.Client() as client:
        response = client.get("https://unmatched")
        assert response.content == b"test content"

        response = client.get("https://test_url")
        assert response.content == b""


def test_request_with_pattern_in_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url")
    httpx_mock.add_response(url="https://unmatched")

    with httpx.Client() as client:
        client.get("https://unmatched")
        client.get("https://test_url", headers={"X-Test": "1"})

    assert httpx_mock.get_request(url=re.compile(".*test.*")).headers["x-test"] == "1"


def test_requests_with_pattern_in_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url")
    httpx_mock.add_response(url="https://tests_url")
    httpx_mock.add_response(url="https://unmatched")

    with httpx.Client() as client:
        client.get("https://tests_url", headers={"X-Test": "1"})
        client.get("https://unmatched", headers={"X-Test": "2"})
        client.get("https://test_url")

    requests = httpx_mock.get_requests(url=re.compile(".*test.*"))
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "1"
    assert "x-test" not in requests[1].headers


def test_callback_with_pattern_in_url(httpx_mock: HTTPXMock):
    def custom_response(request: httpx.Request, *args, **kwargs):
        return httpx.Response(status_code=200, json={"url": str(request.url)})

    def custom_response2(request: httpx.Request, *args, **kwargs):
        return httpx.Response(
            status_code=200,
            extensions={"http_version": b"HTTP/2.0"},
            json={"url": str(request.url)},
        )

    httpx_mock.add_callback(custom_response, url=re.compile(".*test.*"))
    httpx_mock.add_callback(custom_response2, url="https://unmatched")

    with httpx.Client() as client:
        response = client.get("https://unmatched")
        assert response.http_version == "HTTP/2.0"

        response = client.get("https://test_url")
        assert response.http_version == "HTTP/1.1"


def test_with_many_responses_urls_instances(httpx_mock: HTTPXMock):
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

    with httpx.Client() as client:
        response = client.post("https://test_url?param2=test")
        assert response.content == b"test content 2"

        response = client.get("https://test_url?param1=test")
        assert response.content == b"test content 1"

        response = client.put("https://test_url?param3=test")
        assert response.content == b"test content 3"

        response = client.head("https://test_url?param6=test")
        assert response.content == b"test content 6"

        response = client.patch("https://test_url?param5=test")
        assert response.content == b"test content 5"

        response = client.delete("https://test_url?param4=test")
        assert response.content == b"test content 4"


def test_with_http_version_2(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url", http_version="HTTP/2", content=b"test content 1"
    )

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.content == b"test content 1"
        assert response.http_version == "HTTP/2"


def test_with_headers(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url",
        content=b"test content 1",
        headers={"X-Test": "Test value"},
    )

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.content == b"test content 1"
        assert response.headers == httpx.Headers(
            {"x-test": "Test value", "content-length": "14"}
        )


def test_multipart_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url",
        files={"file1": b"content of file 1"},
        boundary=b"2256d3a36d2a61a1eba35a22bee5c74a",
    )
    httpx_mock.add_response(
        url="https://test_url2",
        data={"key1": "value1"},
        files={"file1": b"content of file 1"},
        boundary=b"2256d3a36d2a61a1eba35a22bee5c74a",
    )

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert (
            response.text
            == '--2256d3a36d2a61a1eba35a22bee5c74a\r\nContent-Disposition: form-data; name="file1"; filename="upload"\r\nContent-Type: application/octet-stream\r\n\r\ncontent of file 1\r\n--2256d3a36d2a61a1eba35a22bee5c74a--\r\n'
        )

        response = client.get("https://test_url2")
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


def test_requests_retrieval(httpx_mock: HTTPXMock):
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

    with httpx.Client() as client:
        client.post("https://test_url", content=b"sent content 2")
        client.get("https://test_url", headers={"X-TEST": "test header 1"})
        client.put("https://test_url", content=b"sent content 3")
        client.head("https://test_url")
        client.patch("https://test_url", content=b"sent content 5")
        client.delete("https://test_url", headers={"X-Test": "test header 4"})

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


def test_requests_retrieval_on_same_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url")

    with httpx.Client() as client:
        client.get("https://test_url", headers={"X-TEST": "test header 1"})
        client.get("https://test_url", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests(url=httpx.URL("https://test_url"))
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


def test_request_retrieval_on_same_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        client.get("https://test_url", headers={"X-TEST": "test header 1"})
        client.get("https://test_url2", headers={"X-TEST": "test header 2"})

    request = httpx_mock.get_request(url=httpx.URL("https://test_url"))
    assert request.headers["x-test"] == "test header 1"


def test_requests_retrieval_on_same_method(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        client.get("https://test_url", headers={"X-TEST": "test header 1"})
        client.get("https://test_url2", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests(method="GET")
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


def test_request_retrieval_on_same_method(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        client.get("https://test_url", headers={"X-TEST": "test header 1"})
        client.post("https://test_url", headers={"X-TEST": "test header 2"})

    request = httpx_mock.get_request(method="GET")
    assert request.headers["x-test"] == "test header 1"


def test_requests_retrieval_on_same_url_and_method(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        client.get("https://test_url", headers={"X-TEST": "test header 1"})
        client.get("https://test_url", headers={"X-TEST": "test header 2"})
        client.post("https://test_url", headers={"X-TEST": "test header 3"})
        client.get("https://test_url2", headers={"X-TEST": "test header 4"})

    requests = httpx_mock.get_requests(url=httpx.URL("https://test_url"), method="GET")
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


def test_default_requests_retrieval(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        client.post("https://test_url", headers={"X-TEST": "test header 1"})
        client.get("https://test_url2", headers={"X-TEST": "test header 2"})

    requests = httpx_mock.get_requests()
    assert len(requests) == 2
    assert requests[0].headers["x-test"] == "test header 1"
    assert requests[1].headers["x-test"] == "test header 2"


def test_default_request_retrieval(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        client.post("https://test_url", headers={"X-TEST": "test header 1"})

    request = httpx_mock.get_request()
    assert request.headers["x-test"] == "test header 1"


def test_requests_json_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url", method="GET", json=["list content 1", "list content 2"]
    )
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        json={"key 1": "value 1", "key 2": "value 2"},
    )
    httpx_mock.add_response(url="https://test_url", method="PUT", json="string value")

    with httpx.Client() as client:
        response = client.post("https://test_url")
        assert response.json() == {"key 1": "value 1", "key 2": "value 2"}
        assert response.headers["content-type"] == "application/json"

        response = client.get("https://test_url")
        assert response.json() == ["list content 1", "list content 2"]
        assert response.headers["content-type"] == "application/json"

        response = client.put("https://test_url")
        assert response.json() == "string value"
        assert response.headers["content-type"] == "application/json"


def test_callback_raising_exception(httpx_mock: HTTPXMock):
    def raise_timeout(request, extensions):
        raise httpx.ReadTimeout(
            f"Unable to read within {extensions['timeout']['read']}", request=request
        )

    httpx_mock.add_callback(raise_timeout, url="https://test_url")

    with httpx.Client() as client:
        with pytest.raises(httpx.ReadTimeout) as exception_info:
            client.get("https://test_url")
        assert str(exception_info.value) == "Unable to read within 5.0"


def test_callback_returning_response(httpx_mock: HTTPXMock):
    def custom_response(request: httpx.Request, *args, **kwargs):
        return httpx.Response(status_code=200, json={"url": str(request.url)})

    httpx_mock.add_callback(custom_response, url="https://test_url")

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.json() == {"url": "https://test_url/"}
        assert response.headers["content-type"] == "application/json"


def test_callback_executed_twice(httpx_mock: HTTPXMock):
    def custom_response(*args, **kwargs):
        return httpx.Response(status_code=200, json=["content"])

    httpx_mock.add_callback(custom_response)

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"

        response = client.post("https://test_url")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"


def test_callback_matching_method(httpx_mock: HTTPXMock):
    def custom_response(*args, **kwargs) -> httpx.Response:
        return httpx.Response(status_code=200, json=["content"])

    httpx_mock.add_callback(custom_response, method="GET")

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"

        response = client.get("https://test_url2")
        assert response.json() == ["content"]
        assert response.headers["content-type"] == "application/json"


def test_request_retrieval_with_more_than_one(testdir):
    """
    Single request cannot be returned if there is more than one matching.
    """
    testdir.makepyfile(
        """
        import httpx
        
        
        def test_request_retrieval_with_more_than_one(httpx_mock):
            httpx_mock.add_response()
        
            with httpx.Client() as client:
                client.get("https://test_url", headers={"X-TEST": "test header 1"})
                client.get("https://test_url", headers={"X-TEST": "test header 2"})
        
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


def test_headers_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        match_headers={"user-agent": f"python-httpx/{httpx.__version__}"}
    )

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.content == b""


def test_headers_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
            "host2": "test_url",
        }
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.get("https://test_url")
        assert (
            str(exception_info.value)
            == f"""No response can be found for GET request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers amongst:
Match all requests with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2', 'host2': 'test_url'}} headers"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_content_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_content=b"This is the body")

    with httpx.Client() as client:
        response = client.post("https://test_url", content=b"This is the body")
        assert response.read() == b""


def test_content_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_content=b"This is the body")

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body2")
        assert (
            str(exception_info.value)
            == """No response can be found for POST request on https://test_url with b'This is the body2' body amongst:
Match all requests with b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_headers_and_content_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        match_headers={"user-agent": f"python-httpx/{httpx.__version__}"},
        match_content=b"This is the body",
    )

    with httpx.Client() as client:
        response = client.post("https://test_url", content=b"This is the body")
        assert response.content == b""


def test_headers_not_matching_and_content_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_headers_matching_and_content_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_headers_and_content_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_url_and_headers_and_content_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={"user-agent": f"python-httpx/{httpx.__version__}"},
        match_content=b"This is the body",
    )

    with httpx.Client() as client:
        response = client.post("https://test_url", content=b"This is the body")
        assert response.content == b""


def test_headers_not_matching_and_url_and_content_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_url_and_headers_not_matching_and_content_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url2",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_url_and_headers_matching_and_content_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_headers_matching_and_url_and_content_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url2",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_url_matching_and_headers_and_content_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_url_and_headers_and_content_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url2",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match all requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_method_and_url_and_headers_and_content_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={"user-agent": f"python-httpx/{httpx.__version__}"},
        match_content=b"This is the body",
    )

    with httpx.Client() as client:
        response = client.post("https://test_url", content=b"This is the body")
        assert response.content == b""


def test_headers_not_matching_and_method_and_url_and_content_matching(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_url_and_headers_not_matching_and_method_and_content_matching(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        url="https://test_url2",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_method_and_url_and_headers_matching_and_content_not_matching(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_method_and_headers_matching_and_url_and_content_not_matching(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        url="https://test_url2",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_method_and_url_matching_and_headers_and_content_not_matching(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        url="https://test_url",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_method_matching_and_url_and_headers_and_content_not_matching(
    httpx_mock: HTTPXMock,
):
    httpx_mock.add_response(
        url="https://test_url2",
        method="POST",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match POST requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_method_and_url_and_headers_and_content_not_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://test_url2",
        method="PUT",
        match_headers={
            "user-agent": f"python-httpx/{httpx.__version__}",
            "host": "test_url2",
        },
        match_content=b"This is the body2",
    )

    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException) as exception_info:
            client.post("https://test_url", content=b"This is the body")
        assert (
            str(exception_info.value)
            == f"""No response can be found for POST request on https://test_url with {{'host': 'test_url', 'user-agent': 'python-httpx/{httpx.__version__}'}} headers and b'This is the body' body amongst:
Match PUT requests on https://test_url2 with {{'user-agent': 'python-httpx/{httpx.__version__}', 'host': 'test_url2'}} headers and b'This is the body2' body"""
        )

    # Clean up responses to avoid assertion failure
    httpx_mock.reset(assert_all_responses_were_requested=False)


def test_header_as_str_tuple_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        headers=[("set-cookie", "key=value"), ("set-cookie", "key2=value2")]
    )

    with httpx.Client() as client:
        response = client.get("https://test_url")

    assert dict(response.cookies) == {"key": "value", "key2": "value2"}


def test_header_as_bytes_tuple_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        headers=[(b"set-cookie", b"key=value"), (b"set-cookie", b"key2=value2")]
    )

    with httpx.Client() as client:
        response = client.get("https://test_url")

    assert dict(response.cookies) == {"key": "value", "key2": "value2"}


def test_header_as_bytes_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_response(headers={b"set-cookie": b"key=value"})

    with httpx.Client() as client:
        response = client.get("https://test_url")

    assert dict(response.cookies) == {"key": "value"}


def test_header_as_httpx_headers(httpx_mock: HTTPXMock):
    httpx_mock.add_response(headers=httpx.Headers({"set-cookie": "key=value"}))

    with httpx.Client() as client:
        response = client.get("https://test_url")

    assert dict(response.cookies) == {"key": "value"}
