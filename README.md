<h2 align="center">pytest fixture for HTTPX</h2>

<p align="center">
<a href="https://pypi.org/project/pytest-httpx/"><img alt="pypi version" src="https://img.shields.io/pypi/v/pytest_httpx"></a>
<a href="https://travis-ci.com/Colin-b/pytest_httpx"><img alt="Build status" src="https://api.travis-ci.com/Colin-b/pytest_httpx.svg?branch=master"></a>
<a href="https://travis-ci.com/Colin-b/pytest_httpx"><img alt="Coverage" src="https://img.shields.io/badge/coverage-100%25-brightgreen"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://travis-ci.com/Colin-b/pytest_httpx"><img alt="Number of tests" src="https://img.shields.io/badge/tests-14 passed-blue"></a>
<a href="https://pypi.org/project/pytest-httpx/"><img alt="Number of downloads" src="https://img.shields.io/pypi/dm/pytest_httpx"></a>
</p>

Notice: This module is still under development, versions prior to 1.0.0 are subject to breaking changes without notice.

Use `pytest_httpx.httpx_mock` [`pytest`](https://docs.pytest.org/en/latest/) fixture to mock [`httpx`](https://www.python-httpx.org) requests.

- [Add responses](#add-responses)
  - [JSON body](#add-json-response)
  - [Custom body](#reply-with-custom-body)
  - [HTTP method](#add-non-get-response)
  - [HTTP status code](#add-non-200-response)
  - [HTTP headers](#reply-with-custom-headers)
  - [HTTP/2.0](#add-http/2.0-response)
- [Check requests](#check-sent-requests)

## Add responses

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_something(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")

    response = httpx.get("http://test_url")
```

In case more than one request is sent to the same URL, the responses will be sent in the registration order.

First response will be sent as response of the first request and so on.

If the number of responses is lower than the number of requests on an URL, the last response will be used to reply to all subsequent requests on this URL.

If all responses are not sent back during test execution, the test case will fail at teardown.

Default response is a 200 (OK) without any body for a GET request on the provided URL using HTTP/1.1 protocol version.

Default matching is performed on the full URL, query parameters included.

### Add JSON response

Use `json` parameter to add a JSON response using python values.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_something(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", json=[{"key1": "value1", "key2": "value2"}])

    assert httpx.get("http://test_url").json() == [{"key1": "value1", "key2": "value2"}]
    
```

### Reply with custom body

Use `content` parameter to reply with a custom body by providing bytes or UTF-8 encoded string.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_str_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", content="This is my UTF-8 content")

    assert httpx.get("http://test_url").text == "This is my UTF-8 content"


def test_bytes_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", content=b"This is my bytes content")

    assert httpx.get("http://test_url").content == b"This is my bytes content"
    
```

### Add non GET response

Use `method` parameter to specify the HTTP method (POST, PUT, DELETE, PATCH, HEAD) to reply to on provided URL.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_post(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="POST")

    response = httpx.post("http://test_url")


def test_put(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="PUT")

    response = httpx.put("http://test_url")


def test_delete(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="DELETE")

    response = httpx.delete("http://test_url")


def test_patch(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="PATCH")

    response = httpx.patch("http://test_url")


def test_head(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="HEAD")

    response = httpx.head("http://test_url")
    
```

### Add non 200 response

Use `status_code` parameter to specify the HTTP status code of the response.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_something(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", status_code=404)

    assert httpx.get("http://test_url").status_code == 404

```

### Reply with custom headers

Use `headers` parameter to specify the extra headers of the response.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_something(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", headers={"X-Header1": "Test value"})

    assert httpx.get("http://test_url").headers["x-header1"] == "Test value"

```

### Add HTTP/2.0 response

Use `http_version` parameter to specify the HTTP protocol version of the response.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_something(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", http_version="HTTP/2.0")

    assert httpx.get("http://test_url").http_version == "HTTP/2.0"

```

## Check sent requests

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_something(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")

    response = httpx.get("http://test_url")

    request = httpx_mock.get_request("http://test_url")
```

A request can only be retrieved once per test case. 

Calling order is preserved, so in case more than one request is sent to the same URL, the first one will be returned first.
