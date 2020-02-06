import pytest
import httpx

from pytest_httpx import httpx_mock, HTTPXMock


def test_httpx_mock_without_response(httpx_mock: HTTPXMock):
    with pytest.raises(Exception) as exception_info:
        with httpx.Client() as client:
            client.get("http://test_url")
    assert (
        str(exception_info.value)
        == "No mock can be found for GET request on http://test_url."
    )


def test_httpx_mock_default_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")

    with httpx.Client() as client:
        response = client.get("http://test_url")
    assert response.content == b""
    assert response.status_code == 200
    assert response.headers == httpx.Headers({})
    assert response.http_version == "HTTP/1.1"


def test_httpx_mock_with_one_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", data=b"test content")

    with httpx.Client() as client:
        response = client.get("http://test_url")
        assert response.content == b"test content"

        response = client.get("http://test_url")
        assert response.content == b"test content"


def test_httpx_mock_with_many_responses(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", data=b"test content 1")
    httpx_mock.add_response("http://test_url", data=b"test content 2")

    with httpx.Client() as client:
        response = client.get("http://test_url")
        assert response.content == b"test content 1"

        response = client.get("http://test_url")
        assert response.content == b"test content 2"

        response = client.get("http://test_url")
        assert response.content == b"test content 2"


def test_httpx_mock_with_many_responses_methods(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="GET", data=b"test content 1")
    httpx_mock.add_response("http://test_url", method="POST", data=b"test content 2")
    httpx_mock.add_response("http://test_url", method="PUT", data=b"test content 3")
    httpx_mock.add_response("http://test_url", method="DELETE", data=b"test content 4")
    httpx_mock.add_response("http://test_url", method="PATCH", data=b"test content 5")
    httpx_mock.add_response("http://test_url", method="HEAD", data=b"test content 6")

    with httpx.Client() as client:
        response = client.post("http://test_url")
        assert response.content == b"test content 2"

        response = client.get("http://test_url")
        assert response.content == b"test content 1"

        response = client.put("http://test_url")
        assert response.content == b"test content 3"

        response = client.head("http://test_url")
        assert response.content == b"test content 6"

        response = client.patch("http://test_url")
        assert response.content == b"test content 5"

        response = client.delete("http://test_url")
        assert response.content == b"test content 4"


def test_httpx_mock_with_many_responses_status_codes(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        "http://test_url", method="GET", data=b"test content 1", status_code=200
    )
    httpx_mock.add_response(
        "http://test_url", method="POST", data=b"test content 2", status_code=201
    )
    httpx_mock.add_response(
        "http://test_url", method="PUT", data=b"test content 3", status_code=202
    )
    httpx_mock.add_response(
        "http://test_url", method="DELETE", data=b"test content 4", status_code=303
    )
    httpx_mock.add_response(
        "http://test_url", method="PATCH", data=b"test content 5", status_code=404
    )
    httpx_mock.add_response(
        "http://test_url", method="HEAD", data=b"test content 6", status_code=500
    )

    with httpx.Client() as client:
        response = client.post("http://test_url")
        assert response.content == b"test content 2"
        assert response.status_code == 201

        response = client.get("http://test_url")
        assert response.content == b"test content 1"
        assert response.status_code == 200

        response = client.put("http://test_url")
        assert response.content == b"test content 3"
        assert response.status_code == 202

        response = client.head("http://test_url")
        assert response.content == b"test content 6"
        assert response.status_code == 500

        response = client.patch("http://test_url")
        assert response.content == b"test content 5"
        assert response.status_code == 404

        response = client.delete("http://test_url")
        assert response.content == b"test content 4"
        assert response.status_code == 303


def test_httpx_mock_with_many_responses_urls_str(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        "http://test_url?param1=test", method="GET", data=b"test content 1"
    )
    httpx_mock.add_response(
        "http://test_url?param2=test", method="POST", data=b"test content 2"
    )
    httpx_mock.add_response(
        "http://test_url?param3=test", method="PUT", data=b"test content 3"
    )
    httpx_mock.add_response(
        "http://test_url?param4=test", method="DELETE", data=b"test content 4"
    )
    httpx_mock.add_response(
        "http://test_url?param5=test", method="PATCH", data=b"test content 5"
    )
    httpx_mock.add_response(
        "http://test_url?param6=test", method="HEAD", data=b"test content 6"
    )

    with httpx.Client() as client:
        response = client.post(httpx.URL("http://test_url", params={"param2": "test"}))
        assert response.content == b"test content 2"

        response = client.get(httpx.URL("http://test_url", params={"param1": "test"}))
        assert response.content == b"test content 1"

        response = client.put(httpx.URL("http://test_url", params={"param3": "test"}))
        assert response.content == b"test content 3"

        response = client.head(httpx.URL("http://test_url", params={"param6": "test"}))
        assert response.content == b"test content 6"

        response = client.patch(httpx.URL("http://test_url", params={"param5": "test"}))
        assert response.content == b"test content 5"

        response = client.delete(
            httpx.URL("http://test_url", params={"param4": "test"})
        )
        assert response.content == b"test content 4"


def test_httpx_mock_with_many_responses_urls_instances(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param1": "test"}),
        method="GET",
        data=b"test content 1",
    )
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param2": "test"}),
        method="POST",
        data=b"test content 2",
    )
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param3": "test"}),
        method="PUT",
        data=b"test content 3",
    )
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param4": "test"}),
        method="DELETE",
        data=b"test content 4",
    )
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param5": "test"}),
        method="PATCH",
        data=b"test content 5",
    )
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param6": "test"}),
        method="HEAD",
        data=b"test content 6",
    )

    with httpx.Client() as client:
        response = client.post("http://test_url?param2=test")
        assert response.content == b"test content 2"

        response = client.get("http://test_url?param1=test")
        assert response.content == b"test content 1"

        response = client.put("http://test_url?param3=test")
        assert response.content == b"test content 3"

        response = client.head("http://test_url?param6=test")
        assert response.content == b"test content 6"

        response = client.patch("http://test_url?param5=test")
        assert response.content == b"test content 5"

        response = client.delete("http://test_url?param4=test")
        assert response.content == b"test content 4"


def test_httpx_mock_with_http_version_2(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        "http://test_url", http_version="HTTP/2", data=b"test content 1"
    )

    with httpx.Client() as client:
        response = client.get("http://test_url")
        assert response.content == b"test content 1"
        assert response.http_version == "HTTP/2"


def test_httpx_mock_with_headers(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        "http://test_url", data=b"test content 1", headers={"X-Test": "Test value"}
    )

    with httpx.Client() as client:
        response = client.get("http://test_url")
        assert response.content == b"test content 1"
        assert response.headers == httpx.Headers({"x-test": "Test value"})


def test_httpx_mock_multipart_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", data={"key1": "value1"})
    httpx_mock.add_response(
        "http://test_url",
        files={"file1": "content of file 1"},
        boundary=b"2256d3a36d2a61a1eba35a22bee5c74a",
    )
    httpx_mock.add_response(
        "http://test_url",
        data={"key1": "value1"},
        files={"file1": "content of file 1"},
        boundary=b"2256d3a36d2a61a1eba35a22bee5c74a",
    )

    with httpx.Client() as client:
        response = client.get("http://test_url")
        assert response.text == "key1=value1"

        response = client.get("http://test_url")
        assert (
            response.text
            == '--2256d3a36d2a61a1eba35a22bee5c74a\r\nContent-Disposition: form-data; name="file1"; filename="upload"\r\nContent-Type: application/octet-stream\r\n\r\ncontent of file 1\r\n--2256d3a36d2a61a1eba35a22bee5c74a--\r\n'
        )

        response = client.get("http://test_url")
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


def test_httpx_mock_requests_retrieval(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="GET", data=b"test content 1")
    httpx_mock.add_response("http://test_url", method="POST", data=b"test content 2")
    httpx_mock.add_response("http://test_url", method="PUT", data=b"test content 3")
    httpx_mock.add_response("http://test_url", method="DELETE", data=b"test content 4")
    httpx_mock.add_response("http://test_url", method="PATCH", data=b"test content 5")
    httpx_mock.add_response("http://test_url", method="HEAD", data=b"test content 6")

    with httpx.Client() as client:
        client.post("http://test_url", data=b"sent content 2")
        client.get("http://test_url", headers={"X-TEST": "test header 1"})
        client.put("http://test_url", data=b"sent content 3")
        client.head("http://test_url")
        client.patch("http://test_url", data=b"sent content 5")
        client.delete("http://test_url", headers={"X-Test": "test header 4"})

    assert (
        httpx_mock.get_request(httpx.URL("http://test_url"), "PATCH").read()
        == b"sent content 5"
    )
    assert httpx_mock.get_request(httpx.URL("http://test_url"), "HEAD").read() == b""
    assert (
        httpx_mock.get_request(httpx.URL("http://test_url"), "PUT").read()
        == b"sent content 3"
    )
    assert (
        httpx_mock.get_request(httpx.URL("http://test_url")).headers["x-test"]
        == "test header 1"
    )
    assert (
        httpx_mock.get_request(httpx.URL("http://test_url"), "POST").read()
        == b"sent content 2"
    )
    assert (
        httpx_mock.get_request(httpx.URL("http://test_url"), "DELETE").headers["x-test"]
        == "test header 4"
    )


def test_httpx_mock_requests_retrieval_on_same_url_and_method(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")

    with httpx.Client() as client:
        client.get("http://test_url", headers={"X-TEST": "test header 1"})
        client.get("http://test_url", headers={"X-TEST": "test header 2"})

    assert (
        httpx_mock.get_request(httpx.URL("http://test_url")).headers["x-test"]
        == "test header 1"
    )
    assert (
        httpx_mock.get_request(httpx.URL("http://test_url")).headers["x-test"]
        == "test header 2"
    )
    assert not httpx_mock.get_request(httpx.URL("http://test_url"))


def test_httpx_mock_requests_json_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        "http://test_url", json=["list content 1", "list content 2"]
    )
    httpx_mock.add_response(
        "http://test_url", method="POST", json={"key 1": "value 1", "key 2": "value 2"}
    )
    httpx_mock.add_response("http://test_url", method="PUT", json="string value")

    with httpx.Client() as client:
        response = client.post("http://test_url")
        assert response.json() == {"key 1": "value 1", "key 2": "value 2"}

        response = client.get("http://test_url")
        assert response.json() == ["list content 1", "list content 2"]

        response = client.put("http://test_url")
        assert response.json() == "string value"
