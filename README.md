<h2 align="center">pytest fixture for HTTPX</h2>

<p align="center">
<a href="https://pypi.org/project/pytest-httpx/"><img alt="pypi version" src="https://img.shields.io/pypi/v/pytest_httpx"></a>
<a href="https://travis-ci.com/Colin-b/pytest_httpx"><img alt="Build status" src="https://api.travis-ci.com/Colin-b/pytest_httpx.svg?branch=master"></a>
<a href="https://travis-ci.com/Colin-b/pytest_httpx"><img alt="Coverage" src="https://img.shields.io/badge/coverage-100%25-brightgreen"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://travis-ci.com/Colin-b/pytest_httpx"><img alt="Number of tests" src="https://img.shields.io/badge/tests-64 passed-blue"></a>
<a href="https://pypi.org/project/pytest-httpx/"><img alt="Number of downloads" src="https://img.shields.io/pypi/dm/pytest_httpx"></a>
</p>

Notice: This module is still under development, versions prior to 1.0.0 are subject to breaking changes without notice.

Use `pytest_httpx.httpx_mock` [`pytest`](https://docs.pytest.org/en/latest/) fixture to mock [`httpx`](https://www.python-httpx.org) requests.

- [Add responses](#add-responses)
  - [JSON body](#add-json-response)
  - [Custom body](#reply-with-custom-body)
  - [Multipart body (files, ...)](#add-multipart-response)
  - [HTTP method](#add-non-get-response)
  - [HTTP status code](#add-non-200-response)
  - [HTTP headers](#reply-with-custom-headers)
  - [HTTP/2.0](#add-http/2.0-response)
- [Add dynamic responses](#dynamic-responses)
- [Raising exceptions](#raising-exceptions)
- [Check requests](#check-sent-requests)

## Add responses

You can register responses for both sync and async `httpx` requests.

```python
import pytest
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_something(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        response = client.get("http://test_url")


@pytest.mark.asyncio
async def test_something_async(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        response = await client.get("http://test_url")
```

If all responses are not sent back during test execution, the test case will fail at teardown.

Default response is a HTTP/1.1 200 (OK) without any body.

### How response is selected

In case more than one response match request, the first one not yet sent (according to the registration order) will be sent.

In case all matching responses have been sent, the last one (according to the registration order) will be sent.

You can add criteria so that response will be sent only in case of a more specific matching.

#### Matching on URL

`url` parameter can either be a string, a python re.Pattern instance or a httpx.URL instance.

Matching is performed on the full URL, query parameters included.

#### Matching on HTTP method

`method` parameter must be a string. It will be upper cased so it can be provided lower cased.

Matching is performed on equality.

### Add JSON response

Use `json` parameter to add a JSON response using python values.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_json(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", json=[{"key1": "value1", "key2": "value2"}])

    with httpx.Client() as client:
        assert client.get("http://test_url").json() == [{"key1": "value1", "key2": "value2"}]
    
```

### Reply with custom body

Use `data` parameter to reply with a custom body by providing bytes or UTF-8 encoded string.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_str_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", data="This is my UTF-8 content")

    with httpx.Client() as client:
        assert client.get("http://test_url").text == "This is my UTF-8 content"


def test_bytes_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", data=b"This is my bytes content")

    with httpx.Client() as client:
        assert client.get("http://test_url").content == b"This is my bytes content"
    
```

### Add multipart response

Use `data` parameter as a dictionary or `files` parameter (or both) to send multipart response.

You can specify `boundary` parameter to specify the multipart boundary to use.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_multipart_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", data={"key1": "value1"}, files={"file1": "content of file 1"}, boundary=b"2256d3a36d2a61a1eba35a22bee5c74a")

    with httpx.Client() as client:
        assert client.get("http://test_url").text == '''--2256d3a36d2a61a1eba35a22bee5c74a\r
Content-Disposition: form-data; name="key1"\r
\r
value1\r
--2256d3a36d2a61a1eba35a22bee5c74a\r
Content-Disposition: form-data; name="file1"; filename="upload"\r
Content-Type: application/octet-stream\r
\r
content of file 1\r
--2256d3a36d2a61a1eba35a22bee5c74a--\r
'''
    
```

### Add non GET response

Use `method` parameter to specify the HTTP method (POST, PUT, DELETE, PATCH, HEAD) to reply to on provided URL.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_post(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="POST")

    with httpx.Client() as client:
        response = client.post("http://test_url")


def test_put(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="PUT")

    with httpx.Client() as client:
        response = client.put("http://test_url")


def test_delete(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="DELETE")

    with httpx.Client() as client:
        response = client.delete("http://test_url")


def test_patch(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="PATCH")

    with httpx.Client() as client:
        response = client.patch("http://test_url")


def test_head(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", method="HEAD")

    with httpx.Client() as client:
        response = client.head("http://test_url")
    
```

### Add non 200 response

Use `status_code` parameter to specify the HTTP status code of the response.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_status_code(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", status_code=404)

    with httpx.Client() as client:
        assert client.get("http://test_url").status_code == 404

```

### Reply with custom headers

Use `headers` parameter to specify the extra headers of the response.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_headers(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", headers={"X-Header1": "Test value"})

    with httpx.Client() as client:
        assert client.get("http://test_url").headers["x-header1"] == "Test value"

```

### Add HTTP/2.0 response

Use `http_version` parameter to specify the HTTP protocol version of the response.

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_http_version(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url", http_version="HTTP/2.0")

    with httpx.Client() as client:
        assert client.get("http://test_url").http_version == "HTTP/2.0"

```

## Add callbacks

You can perform custom manipulation upon request reception by registering callbacks.

Callback should expect at least two parameters:
 * request: The received request.
 * timeout: The timeout linked to the request.

If all callbacks are not executed during test execution, the test case will fail at teardown.

### Dynamic responses

Callback should return a httpx.Response instance.

```python
import httpx
from httpx import content_streams
from pytest_httpx import httpx_mock, HTTPXMock


def test_dynamic_response(httpx_mock: HTTPXMock):
    def custom_response(request: httpx.Request, *args, **kwargs) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            http_version="HTTP/1.1",
            headers=[],
            stream=content_streams.JSONStream({"url": str(request.url)}),
            request=request,
        )

    httpx_mock.add_callback(custom_response, "http://test_url")

    with httpx.Client() as client:
        response = client.get("http://test_url")
        assert response.json() == {"url": "http://test_url"}

```

### Raising exceptions

You can simulate httpx exception throwing by raising an exception in your callback.

This can be useful if you want to assert that your code handles httpx exceptions properly.

```python
import httpx
import pytest
from pytest_httpx import httpx_mock, HTTPXMock


def test_exception_raising(httpx_mock: HTTPXMock):
    def raise_timeout(*args, **kwargs) -> httpx.Response:
        raise httpx.exceptions.TimeoutException()

    httpx_mock.add_callback(raise_timeout, "http://test_url")
    
    with httpx.Client() as client:
        with pytest.raises(httpx.exceptions.TimeoutException):
            client.get("http://test_url")

```

### How callback is selected

In case more than one callback match request, the first one not yet executed (according to the registration order) will be executed.

In case all matching callbacks have been executed, the last one (according to the registration order) will be executed.

You can add criteria so that callback will be sent only in case of a more specific matching.

#### Matching on URL

`url` parameter can either be a string, a python re.Pattern instance or a httpx.URL instance.

Matching is performed on the full URL, query parameters included.

#### Matching on HTTP method

`method` parameter must be a string. It will be upper cased so it can be provided lower cased.

Matching is performed on equality.

## Check sent requests

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_many_requests(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")

    with httpx.Client() as client:
        response1 = client.get("http://test_url")
        response2 = client.get("http://test_url")

    requests = httpx_mock.get_requests("http://test_url")


def test_single_request(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")

    with httpx.Client() as client:
        response = client.get("http://test_url")

    request = httpx_mock.get_request("http://test_url")
```

### How requests are selected

You can add criteria so that requests will be returned only in case of a more specific matching.

#### Matching on URL

`url` parameter can either be a string, a python re.Pattern instance or a httpx.URL instance.

Matching is performed on the full URL, query parameters included.

#### Matching on HTTP method

`method` parameter must be a string. It will be upper cased so it can be provided lower cased.

Matching is performed on equality.
