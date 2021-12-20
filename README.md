<h2 align="center">Send responses to HTTPX using pytest</h2>

<p align="center">
<a href="https://pypi.org/project/pytest-httpx/"><img alt="pypi version" src="https://img.shields.io/pypi/v/pytest_httpx"></a>
<a href="https://github.com/Colin-b/pytest_httpx/actions"><img alt="Build status" src="https://github.com/Colin-b/pytest_httpx/workflows/Release/badge.svg"></a>
<a href="https://github.com/Colin-b/pytest_httpx/actions"><img alt="Coverage" src="https://img.shields.io/badge/coverage-100%25-brightgreen"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://github.com/Colin-b/pytest_httpx/actions"><img alt="Number of tests" src="https://img.shields.io/badge/tests-144 passed-blue"></a>
<a href="https://pypi.org/project/pytest-httpx/"><img alt="Number of downloads" src="https://img.shields.io/pypi/dm/pytest_httpx"></a>
</p>

> Version 1.0.0 will be released once httpx is considered as stable (release of 1.0.0).
>
> However, current state can be considered as stable.

Once installed, `httpx_mock` [`pytest`](https://docs.pytest.org/en/latest/) fixture will make sure every [`httpx`](https://www.python-httpx.org) request will be replied to with user provided responses.

- [Add responses](#add-responses)
  - [JSON body](#add-json-response)
  - [Custom body](#reply-with-custom-body)
  - [Multipart body (files, ...)](#add-multipart-response)
  - [HTTP status code](#add-non-200-response)
  - [HTTP headers](#reply-with-custom-headers)
  - [HTTP/2.0](#add-http/2.0-response)
- [Add dynamic responses](#dynamic-responses)
- [Raising exceptions](#raising-exceptions)
- [Check requests](#check-sent-requests)
- [Do not mock some requests](#do-not-mock-some-requests)
- [Migrating](#migrating-to-pytest-httpx)
  - [responses](#from-responses)
  - [aioresponses](#from-aioresponses)

## Add responses

You can register responses for both sync and async [`HTTPX`](https://www.python-httpx.org) requests.

```python
import pytest
import httpx


def test_something(httpx_mock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        response = client.get("https://test_url")


@pytest.mark.asyncio
async def test_something_async(httpx_mock):
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")
```

If all registered responses are not sent back during test execution, the test case will fail at teardown.

This behavior can be disabled thanks to the `assert_all_responses_were_requested` fixture:

```python
import pytest

@pytest.fixture
def assert_all_responses_were_requested() -> bool:
    return False
```

Default response is a HTTP/1.1 200 (OK) without any body.

### How response is selected

In case more than one response match request, the first one not yet sent (according to the registration order) will be sent.

In case all matching responses have been sent, the last one (according to the registration order) will be sent.

You can add criteria so that response will be sent only in case of a more specific matching.

#### Matching on URL

`url` parameter can either be a string, a python [re.Pattern](https://docs.python.org/3/library/re.html) instance or a [httpx.URL](https://www.python-httpx.org/api/#url) instance.

Matching is performed on the full URL, query parameters included.

Order of parameters in the query string does not matter, however order of values do matter if the same parameter is provided more than once.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url?a=1&b=2")

    with httpx.Client() as client:
        response1 = client.delete("https://test_url?a=1&b=2")
        response2 = client.get("https://test_url?b=2&a=1")
```

#### Matching on HTTP method

Use `method` parameter to specify the HTTP method (POST, PUT, DELETE, PATCH, HEAD) to reply to.

`method` parameter must be a string. It will be upper-cased, so it can be provided lower cased.

Matching is performed on equality.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_post(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="POST")

    with httpx.Client() as client:
        response = client.post("https://test_url")


def test_put(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="PUT")

    with httpx.Client() as client:
        response = client.put("https://test_url")


def test_delete(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="DELETE")

    with httpx.Client() as client:
        response = client.delete("https://test_url")


def test_patch(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="PATCH")

    with httpx.Client() as client:
        response = client.patch("https://test_url")


def test_head(httpx_mock: HTTPXMock):
    httpx_mock.add_response(method="HEAD")

    with httpx.Client() as client:
        response = client.head("https://test_url")
    
```

#### Matching on HTTP headers

Use `match_headers` parameter to specify the HTTP headers to reply to.

Matching is performed on equality for each provided header.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_headers_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_headers={'user-agent': 'python-httpx/0.21.0'})

    with httpx.Client() as client:
        response = client.get("https://test_url")
```

#### Matching on HTTP body

Use `match_content` parameter to specify the full HTTP body to reply to.

Matching is performed on equality.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_content_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_content=b"This is the body")

    with httpx.Client() as client:
        response = client.post("https://test_url", content=b"This is the body")
```

### Add JSON response

Use `json` parameter to add a JSON response using python values.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_json(httpx_mock: HTTPXMock):
    httpx_mock.add_response(json=[{"key1": "value1", "key2": "value2"}])

    with httpx.Client() as client:
        assert client.get("https://test_url").json() == [{"key1": "value1", "key2": "value2"}]
    
```

Note that the `content-type` header will be set to `application/json` by default in the response.

### Reply with custom body

Use `text` parameter to reply with a custom body by providing UTF-8 encoded string.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_str_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(text="This is my UTF-8 content")

    with httpx.Client() as client:
        assert client.get("https://test_url").text == "This is my UTF-8 content"

```

Use `content` parameter to reply with a custom body by providing bytes.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_bytes_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(content=b"This is my bytes content")

    with httpx.Client() as client:
        assert client.get("https://test_url").content == b"This is my bytes content"
    
```

Use `html` parameter to reply with a custom body by providing UTF-8 encoded string.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_html_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(html="<body>This is <p> HTML content</body>")

    with httpx.Client() as client:
        assert client.get("https://test_url").text == "<body>This is <p> HTML content</body>"

```

### Reply by streaming chunks

Use `stream` parameter to stream chunks that you specify.

```python
import httpx
import pytest
from pytest_httpx import HTTPXMock, IteratorStream

def test_sync_streaming(httpx_mock: HTTPXMock):
    httpx_mock.add_response(stream=IteratorStream([b"part 1", b"part 2"]))

    with httpx.Client() as client:
        with client.stream(method="GET", url="https://test_url") as response:
            assert list(response.iter_raw()) == [b"part 1", b"part 2"]


@pytest.mark.asyncio
async def test_async_streaming(httpx_mock: HTTPXMock):
    httpx_mock.add_response(stream=IteratorStream([b"part 1", b"part 2"]))

    async with httpx.AsyncClient() as client:
        async with client.stream(method="GET", url="https://test_url") as response:
            assert [part async for part in response.aiter_raw()] == [b"part 1", b"part 2"]
    
```

### Add multipart response

Use `files` parameter (and optionally `data` parameter as a dictionary) to send multipart response.

You can specify `boundary` parameter to specify the multipart boundary to use.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_multipart_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(data={"key1": "value1"}, files={"file1": b"content of file 1"}, boundary=b"2256d3a36d2a61a1eba35a22bee5c74a")

    with httpx.Client() as client:
        assert client.get("https://test_url").text == '''--2256d3a36d2a61a1eba35a22bee5c74a\r
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

### Add non 200 response

Use `status_code` parameter to specify the HTTP status code of the response.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_status_code(httpx_mock: HTTPXMock):
    httpx_mock.add_response(status_code=404)

    with httpx.Client() as client:
        assert client.get("https://test_url").status_code == 404

```

### Reply with custom headers

Use `headers` parameter to specify the extra headers of the response.

Any valid httpx headers type is supported, you can submit headers as a dict (str or bytes), a list of 2-tuples (str or bytes) or a `httpx.Header` instance.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_headers_as_str_dict(httpx_mock: HTTPXMock):
    httpx_mock.add_response(headers={"X-Header1": "Test value"})

    with httpx.Client() as client:
        assert client.get("https://test_url").headers["x-header1"] == "Test value"


def test_headers_as_str_tuple_list(httpx_mock: HTTPXMock):
    httpx_mock.add_response(headers=[("X-Header1", "Test value")])

    with httpx.Client() as client:
        assert client.get("https://test_url").headers["x-header1"] == "Test value"


def test_headers_as_httpx_headers(httpx_mock: HTTPXMock):
    httpx_mock.add_response(headers=httpx.Headers({b"X-Header1": b"Test value"}))

    with httpx.Client() as client:
        assert client.get("https://test_url").headers["x-header1"] == "Test value"

```

#### Reply with cookies

Cookies are sent in the `set-cookie` HTTP header.

You can then send cookies in the response by setting the `set-cookie` header with [the value following key=value format]((https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie)).

```python
import httpx
from pytest_httpx import HTTPXMock


def test_cookie(httpx_mock: HTTPXMock):
    httpx_mock.add_response(headers={"set-cookie": "key=value"})

    with httpx.Client() as client:
        response = client.get("https://test_url")
    assert dict(response.cookies) == {"key": "value"}


def test_cookies(httpx_mock: HTTPXMock):
    httpx_mock.add_response(headers=[("set-cookie", "key=value"), ("set-cookie", "key2=value2")])

    with httpx.Client() as client:
        response = client.get("https://test_url")
    assert dict(response.cookies) == {"key": "value", "key2": "value2"}

```


### Add HTTP/2.0 response

Use `http_version` parameter to specify the HTTP protocol version of the response.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_http_version(httpx_mock: HTTPXMock):
    httpx_mock.add_response(http_version="HTTP/2.0")

    with httpx.Client() as client:
        assert client.get("https://test_url").http_version == "HTTP/2.0"

```

## Add callbacks

You can perform custom manipulation upon request reception by registering callbacks.

Callback should expect one parameter, the received [`httpx.Request`](https://www.python-httpx.org/api/#request).

If all callbacks are not executed during test execution, the test case will fail at teardown.

This behavior can be disabled thanks to the `assert_all_responses_were_requested` fixture:

```python
import pytest

@pytest.fixture
def assert_all_responses_were_requested() -> bool:
    return False
```

### Dynamic responses

Callback should return a `httpx.Response`.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_dynamic_response(httpx_mock: HTTPXMock):
    def custom_response(request: httpx.Request):
        return httpx.Response(
            status_code=200, json={"url": str(request.url)},
        )

    httpx_mock.add_callback(custom_response)

    with httpx.Client() as client:
        response = client.get("https://test_url")
        assert response.json() == {"url": "https://test_url"}

```

### Raising exceptions

You can simulate HTTPX exception throwing by raising an exception in your callback.

This can be useful if you want to assert that your code handles HTTPX exceptions properly.

```python
import httpx
import pytest
from pytest_httpx import HTTPXMock


def test_exception_raising(httpx_mock: HTTPXMock):
    def raise_timeout(request: httpx.Request):
        raise httpx.ReadTimeout(f"Unable to read within {request.extensions['timeout']['read']}", request=request)

    httpx_mock.add_callback(raise_timeout)
    
    with httpx.Client() as client:
        with pytest.raises(httpx.ReadTimeout):
            client.get("https://test_url")

```

Note that default behavior is to send an `httpx.TimeoutException` in case no response can be found. You can then test this kind of exception this way:

```python
import httpx
import pytest
from pytest_httpx import HTTPXMock


def test_timeout(httpx_mock: HTTPXMock):
    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException):
            client.get("https://test_url")

```

### How callback is selected

In case more than one callback match request, the first one not yet executed (according to the registration order) will be executed.

In case all matching callbacks have been executed, the last one (according to the registration order) will be executed.

You can add criteria so that callback will be sent only in case of a more specific matching.

#### Matching on URL

`url` parameter can either be a string, a python [`re.Pattern`](https://docs.python.org/3/library/re.html) instance or a [`httpx.URL`](https://www.python-httpx.org/api/#url) instance.

Matching is performed on the full URL, query parameters included.

#### Matching on HTTP method

Use `method` parameter to specify the HTTP method (POST, PUT, DELETE, PATCH, HEAD) executing the callback.

`method` parameter must be a string. It will be upper-cased, so it can be provided lower cased.

Matching is performed on equality.

#### Matching on HTTP headers

Use `match_headers` parameter to specify the HTTP headers executing the callback.

Matching is performed on equality for each provided header.

#### Matching on HTTP body

Use `match_content` parameter to specify the full HTTP body executing the callback.

Matching is performed on equality.

## Check sent requests

The best way to ensure the content of your requests is still to use the `match_headers` and / or `match_content` parameters when adding a response.
In the same spirit, ensuring that no request was issued does not necessarily requires any code.

In any case, you always have the ability to retrieve the requests that were issued.

As in the following samples:

```python
import httpx
from pytest_httpx import HTTPXMock


def test_many_requests(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        response1 = client.get("https://test_url")
        response2 = client.get("https://test_url")

    requests = httpx_mock.get_requests()


def test_single_request(httpx_mock: HTTPXMock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        response = client.get("https://test_url")

    request = httpx_mock.get_request()


def test_no_request(httpx_mock: HTTPXMock):
    assert not httpx_mock.get_request()
```

### How requests are selected

You can add criteria so that requests will be returned only in case of a more specific matching.

#### Matching on URL

`url` parameter can either be a string, a python [re.Pattern](https://docs.python.org/3/library/re.html) instance or a [httpx.URL](https://www.python-httpx.org/api/#url) instance.

Matching is performed on the full URL, query parameters included.

#### Matching on HTTP method

Use `method` parameter to specify the HTTP method (POST, PUT, DELETE, PATCH, HEAD) of the requests to retrieve.

`method` parameter must be a string. It will be upper-cased, so it can be provided lower cased.

Matching is performed on equality.

#### Matching on HTTP headers

Use `match_headers` parameter to specify the HTTP headers executing the callback.

Matching is performed on equality for each provided header.

#### Matching on HTTP body

Use `match_content` parameter to specify the full HTTP body executing the callback.

Matching is performed on equality.

## Do not mock some requests

By default, `pytest-httpx` will mock every request.

But, for instance, in case you want to write integration tests with other servers, you might want to let some requests go through.

To do so, you can use the `non_mocked_hosts` fixture:

```python
import pytest

@pytest.fixture
def non_mocked_hosts() -> list:
    return ["my_local_test_host", "my_other_test_host"]
```

Every other requested hosts will be mocked as in the following example

```python
import pytest
import httpx

@pytest.fixture
def non_mocked_hosts() -> list:
    return ["my_local_test_host"]


def test_partial_mock(httpx_mock):
    httpx_mock.add_response()

    with httpx.Client() as client:
        # This request will NOT be mocked
        response1 = client.get("https://www.my_local_test_host/sub?param=value")
        # This request will be mocked
        response2 = client.get("https://test_url")
```

## Migrating to pytest-httpx

Here is how to migrate from well-known testing libraries to `pytest-httpx`.

### From responses

| Feature           | responses                  | pytest-httpx                |
|:------------------|:---------------------------|:----------------------------|
| Add a response    | `responses.add()`          | `httpx_mock.add_response()` |
| Add a callback    | `responses.add_callback()` | `httpx_mock.add_callback()` |
| Retrieve requests | `responses.calls`          | `httpx_mock.get_requests()` |

#### Add a response or a callback

Undocumented parameters means that they are unchanged between `responses` and `pytest-httpx`.
Below is a list of parameters that will require a change in your code.

| Parameter            | responses                           | pytest-httpx                                                         |
|:---------------------|:------------------------------------|:---------------------------------------------------------------------|
| method               | `method=responses.GET`              | `method="GET"`                                                       |
| body (as bytes)      | `body=b"sample"`                    | `content=b"sample"`                                                  |
| body (as str)        | `body="sample"`                     | `text="sample"`                                                      |
| status code          | `status=201`                        | `status_code=201`                                                    |
| headers              | `adding_headers={"name": "value"}`  | `headers={"name": "value"}`                                          |
| content-type header  | `content_type="application/custom"` | `headers={"content-type": "application/custom"}`                     |
| Match the full query | `match_querystring=True`            | The full query is always matched when providing the `url` parameter. |

Sample adding a response with `responses`:
```python
from responses import RequestsMock

def test_response(responses: RequestsMock):
    responses.add(
        method=responses.GET,
        url="https://test_url",
        body=b"This is the response content",
        status=400,
    )

```

Sample adding the same response with `pytest-httpx`:
```python
from pytest_httpx import HTTPXMock

def test_response(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        method="GET",
        url="https://test_url",
        content=b"This is the response content",
        status_code=400,
    )

```

### From aioresponses

| Feature        | aioresponses            | pytest-httpx                               |
|:---------------|:------------------------|:-------------------------------------------|
| Add a response | `aioresponses.method()` | `httpx_mock.add_response(method="METHOD")` |
| Add a callback | `aioresponses.method()` | `httpx_mock.add_callback(method="METHOD")` |

#### Add a response or a callback

Undocumented parameters means that they are unchanged between `responses` and `pytest-httpx`.
Below is a list of parameters that will require a change in your code.

| Parameter       | responses            | pytest-httpx        |
|:----------------|:---------------------|:--------------------|
| body (as bytes) | `body=b"sample"`     | `content=b"sample"` |
| body (as str)   | `body="sample"`      | `text="sample"`     |
| body (as JSON)  | `payload=["sample"]` | `json=["sample"]`   |
| status code     | `status=201`         | `status_code=201`   |

Sample adding a response with `aioresponses`:
```python
import pytest
from aioresponses import aioresponses


@pytest.fixture
def mock_aioresponse():
    with aioresponses() as m:
        yield m


def test_response(mock_aioresponse):
    mock_aioresponse.get(
        url="https://test_url",
        body=b"This is the response content",
        status=400,
    )

```

Sample adding the same response with `pytest-httpx`:
```python
def test_response(httpx_mock):
    httpx_mock.add_response(
        method="GET",
        url="https://test_url",
        content=b"This is the response content",
        status_code=400,
    )

```
