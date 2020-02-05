import pytest
import httpx

from pytest_httpx import httpx_mock, HTTPXMock


def test_httpx_mock_without_response(httpx_mock: HTTPXMock):
    with pytest.raises(Exception) as exception_info:
        httpx.get("http://test_url")
    assert (
        str(exception_info.value)
        == "No mock can be found for GET request on http://test_url."
    )


@pytest.mark.xfail(
    raises=AssertionError, reason="Unused responses should fail test case."
)
def test_httpx_mock_unused_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")


def test_httpx_mock_default_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")

    response = httpx.get("http://test_url")
    assert response.content == b""
    assert response.status_code == 200
    assert response.headers == httpx.Headers({})
    assert response.http_version == "HTTP/1.1"


def test_httpx_mock_with_one_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", content=b"test content")

    response = httpx.get("http://test_url")
    assert response.content == b"test content"

    response = httpx.get("http://test_url")
    assert response.content == b"test content"


def test_httpx_mock_with_many_responses(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", content=b"test content 1")
    httpx_mock.add_response("http://test_url", content=b"test content 2")

    response = httpx.get("http://test_url")
    assert response.content == b"test content 1"

    response = httpx.get("http://test_url")
    assert response.content == b"test content 2"

    response = httpx.get("http://test_url")
    assert response.content == b"test content 2"


def test_httpx_mock_with_many_responses_methods(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="GET", content=b"test content 1")
    httpx_mock.add_response("http://test_url", method="POST", content=b"test content 2")
    httpx_mock.add_response("http://test_url", method="PUT", content=b"test content 3")
    httpx_mock.add_response(
        "http://test_url", method="DELETE", content=b"test content 4"
    )
    httpx_mock.add_response(
        "http://test_url", method="PATCH", content=b"test content 5"
    )
    httpx_mock.add_response("http://test_url", method="HEAD", content=b"test content 6")

    response = httpx.post("http://test_url")
    assert response.content == b"test content 2"

    response = httpx.get("http://test_url")
    assert response.content == b"test content 1"

    response = httpx.put("http://test_url")
    assert response.content == b"test content 3"

    response = httpx.head("http://test_url")
    assert response.content == b"test content 6"

    response = httpx.patch("http://test_url")
    assert response.content == b"test content 5"

    response = httpx.delete("http://test_url")
    assert response.content == b"test content 4"


def test_httpx_mock_with_many_responses_status_codes(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        "http://test_url", method="GET", content=b"test content 1", status_code=200
    )
    httpx_mock.add_response(
        "http://test_url", method="POST", content=b"test content 2", status_code=201
    )
    httpx_mock.add_response(
        "http://test_url", method="PUT", content=b"test content 3", status_code=202
    )
    httpx_mock.add_response(
        "http://test_url", method="DELETE", content=b"test content 4", status_code=303
    )
    httpx_mock.add_response(
        "http://test_url", method="PATCH", content=b"test content 5", status_code=404
    )
    httpx_mock.add_response(
        "http://test_url", method="HEAD", content=b"test content 6", status_code=500
    )

    response = httpx.post("http://test_url")
    assert response.content == b"test content 2"
    assert response.status_code == 201

    response = httpx.get("http://test_url")
    assert response.content == b"test content 1"
    assert response.status_code == 200

    response = httpx.put("http://test_url")
    assert response.content == b"test content 3"
    assert response.status_code == 202

    response = httpx.head("http://test_url")
    assert response.content == b"test content 6"
    assert response.status_code == 500

    response = httpx.patch("http://test_url")
    assert response.content == b"test content 5"
    assert response.status_code == 404

    response = httpx.delete("http://test_url")
    assert response.content == b"test content 4"
    assert response.status_code == 303


def test_httpx_mock_with_many_responses_urls_str(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        "http://test_url?param1=test", method="GET", content=b"test content 1"
    )
    httpx_mock.add_response(
        "http://test_url?param2=test", method="POST", content=b"test content 2"
    )
    httpx_mock.add_response(
        "http://test_url?param3=test", method="PUT", content=b"test content 3"
    )
    httpx_mock.add_response(
        "http://test_url?param4=test", method="DELETE", content=b"test content 4"
    )
    httpx_mock.add_response(
        "http://test_url?param5=test", method="PATCH", content=b"test content 5"
    )
    httpx_mock.add_response(
        "http://test_url?param6=test", method="HEAD", content=b"test content 6"
    )

    response = httpx.post(httpx.URL("http://test_url", params={"param2": "test"}))
    assert response.content == b"test content 2"

    response = httpx.get(httpx.URL("http://test_url", params={"param1": "test"}))
    assert response.content == b"test content 1"

    response = httpx.put(httpx.URL("http://test_url", params={"param3": "test"}))
    assert response.content == b"test content 3"

    response = httpx.head(httpx.URL("http://test_url", params={"param6": "test"}))
    assert response.content == b"test content 6"

    response = httpx.patch(httpx.URL("http://test_url", params={"param5": "test"}))
    assert response.content == b"test content 5"

    response = httpx.delete(httpx.URL("http://test_url", params={"param4": "test"}))
    assert response.content == b"test content 4"


def test_httpx_mock_with_many_responses_urls_instances(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param1": "test"}),
        method="GET",
        content=b"test content 1",
    )
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param2": "test"}),
        method="POST",
        content=b"test content 2",
    )
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param3": "test"}),
        method="PUT",
        content=b"test content 3",
    )
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param4": "test"}),
        method="DELETE",
        content=b"test content 4",
    )
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param5": "test"}),
        method="PATCH",
        content=b"test content 5",
    )
    httpx_mock.add_response(
        httpx.URL("http://test_url", params={"param6": "test"}),
        method="HEAD",
        content=b"test content 6",
    )

    response = httpx.post("http://test_url?param2=test")
    assert response.content == b"test content 2"

    response = httpx.get("http://test_url?param1=test")
    assert response.content == b"test content 1"

    response = httpx.put("http://test_url?param3=test")
    assert response.content == b"test content 3"

    response = httpx.head("http://test_url?param6=test")
    assert response.content == b"test content 6"

    response = httpx.patch("http://test_url?param5=test")
    assert response.content == b"test content 5"

    response = httpx.delete("http://test_url?param4=test")
    assert response.content == b"test content 4"


def test_httpx_mock_with_http_version_2(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        "http://test_url", http_version="HTTP/2", content=b"test content 1"
    )

    response = httpx.get("http://test_url")
    assert response.content == b"test content 1"
    assert response.http_version == "HTTP/2"


def test_httpx_mock_with_headers(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        "http://test_url", content=b"test content 1", headers={"X-Test": "Test value"}
    )

    response = httpx.get("http://test_url")
    assert response.content == b"test content 1"
    assert response.headers == httpx.Headers({"x-test": "Test value"})


def test_httpx_mock_requests_retrieval(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="GET", content=b"test content 1")
    httpx_mock.add_response("http://test_url", method="POST", content=b"test content 2")
    httpx_mock.add_response("http://test_url", method="PUT", content=b"test content 3")
    httpx_mock.add_response(
        "http://test_url", method="DELETE", content=b"test content 4"
    )
    httpx_mock.add_response(
        "http://test_url", method="PATCH", content=b"test content 5"
    )
    httpx_mock.add_response("http://test_url", method="HEAD", content=b"test content 6")

    httpx.post("http://test_url", data=b"sent content 2")
    httpx.get("http://test_url", headers={"X-TEST": "test header 1"})
    httpx.put("http://test_url", data=b"sent content 3")
    httpx.head("http://test_url")
    httpx.patch("http://test_url", data=b"sent content 5")
    httpx.delete("http://test_url", headers={"X-Test": "test header 4"})

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

    httpx.get("http://test_url", headers={"X-TEST": "test header 1"})
    httpx.get("http://test_url", headers={"X-TEST": "test header 2"})

    assert (
        httpx_mock.get_request(httpx.URL("http://test_url")).headers["x-test"]
        == "test header 1"
    )
    assert (
        httpx_mock.get_request(httpx.URL("http://test_url")).headers["x-test"]
        == "test header 2"
    )
    assert not httpx_mock.get_request(httpx.URL("http://test_url"))
