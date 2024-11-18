<h2 align="center">Send responses to HTTPX using pytest</h2>

<p align="center">
<a href="https://pypi.org/project/pytest-httpx/"><img alt="pypi version" src="https://img.shields.io/pypi/v/pytest_httpx"></a>
<a href="https://github.com/Colin-b/pytest_httpx/actions"><img alt="Build status" src="https://github.com/Colin-b/pytest_httpx/workflows/Release/badge.svg"></a>
<a href="https://github.com/Colin-b/pytest_httpx/actions"><img alt="Coverage" src="https://img.shields.io/badge/coverage-100%25-brightgreen"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://github.com/Colin-b/pytest_httpx/actions"><img alt="Number of tests" src="https://img.shields.io/badge/tests-272 passed-blue"></a>
<a href="https://pypi.org/project/pytest-httpx/"><img alt="Number of downloads" src="https://img.shields.io/pypi/dm/pytest_httpx"></a>
</p>

> [!NOTE]  
> Version 1.0.0 will be released once httpx is considered as stable (release of 1.0.0).
>
> However, current state can be considered as stable.

Once installed, `httpx_mock` [`pytest`](https://docs.pytest.org/en/latest/) fixture will make sure every [`httpx`](https://www.python-httpx.org) request will be replied to with user provided responses ([unless some hosts are explicitly skipped](#do-not-mock-some-requests)).

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
- [Configuration](#configuring-httpx_mock)
  - [Register more responses than requested](#allow-to-register-more-responses-than-what-will-be-requested)
  - [Register less responses than requested](#allow-to-not-register-responses-for-every-request)
  - [Allow to register a response for more than one request](#allow-to-register-a-response-for-more-than-one-request)
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

If all registered responses are not sent back during test execution, the test case will fail at teardown [(unless you turned `assert_all_responses_were_requested` option off)](#allow-to-register-more-responses-than-what-will-be-requested).

Default response is a `HTTP/1.1` `200 (OK)` without any body.

### How response is selected

In case more than one response match request, the first one not yet sent (according to the registration order) will be sent.

In case all matching responses have been sent once, the request will [not be considered as matched](#in-case-no-response-can-be-found) [(unless you turned `can_send_already_matched_responses` option on)](#allow-to-register-a-response-for-more-than-one-request).

You can add criteria so that response will be sent only in case of a more specific matching.

#### Matching on URL

`url` parameter can either be a string, a python [re.Pattern](https://docs.python.org/3/library/re.html) instance or a [httpx.URL](https://www.python-httpx.org/api/#url) instance.

Matching is performed on the full URL, query parameters included.

Order of parameters in the query string does not matter, however order of values do matter if the same parameter is provided more than once.

```python
import httpx
import re
from pytest_httpx import HTTPXMock


def test_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url="https://test_url?a=1&b=2")

    with httpx.Client() as client:
        response1 = client.delete("https://test_url?a=1&b=2")
        response2 = client.get("https://test_url?b=2&a=1")


def test_url_as_pattern(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=re.compile(".*test.*"))

    with httpx.Client() as client:
        response = client.get("https://test_url")


def test_url_as_httpx_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=httpx.URL("https://test_url", params={"a": "1", "b": "2"}))

    with httpx.Client() as client:
        response = client.get("https://test_url?a=1&b=2")
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

#### Matching on proxy URL

`proxy_url` parameter can either be a string, a python [re.Pattern](https://docs.python.org/3/library/re.html) instance or a [httpx.URL](https://www.python-httpx.org/api/#url) instance.

Matching is performed on the full proxy URL, query parameters included.

Order of parameters in the query string does not matter, however order of values do matter if the same parameter is provided more than once.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_proxy_url(httpx_mock: HTTPXMock):
    httpx_mock.add_response(proxy_url="http://test_proxy_url?b=1&a=2")

    with httpx.Client(proxy="http://test_proxy_url?a=2&b=1") as client:
        response = client.get("https://test_url")
```

#### Matching on HTTP headers

Use `match_headers` parameter to specify the HTTP headers (as a dict) to reply to.

Matching is performed on equality for each provided header.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_headers_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_headers={'User-Agent': 'python-httpx/0.25.0'})

    with httpx.Client() as client:
        response = client.get("https://test_url")
```

#### Matching on HTTP body

Use `match_content` parameter to specify the full HTTP body (as bytes) to reply to.

Matching is performed on equality.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_content_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_content=b"This is the body")

    with httpx.Client() as client:
        response = client.post("https://test_url", content=b"This is the body")
```

##### Matching on HTTP JSON body

Use `match_json` parameter to specify the JSON decoded HTTP body to reply to.

Matching is performed on equality. You can however use `unittest.mock.ANY` to do partial matching.

```python
import httpx
from pytest_httpx import HTTPXMock
from unittest.mock import ANY

def test_json_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_json={"a": "json", "b": 2})

    with httpx.Client() as client:
        response = client.post("https://test_url", json={"a": "json", "b": 2})

        
def test_partial_json_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_json={"a": "json", "b": ANY})

    with httpx.Client() as client:
        response = client.post("https://test_url", json={"a": "json", "b": 2})
```
        
Note that `match_content` or `match_files` cannot be provided if `match_json` is also provided.

##### Matching on HTTP multipart body

Use `match_files` and `match_data` parameters to specify the full multipart body to reply to.

Matching is performed on equality.

```python
import httpx
from pytest_httpx import HTTPXMock

def test_multipart_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_files={"name": ("file_name", b"File content")}, match_data={"field": "value"})

    with httpx.Client() as client:
        response = client.post("https://test_url", files={"name": ("file_name", b"File content")}, data={"field": "value"})
```
        
Note that `match_content` or `match_json` cannot be provided if `match_files` is also provided.

#### Matching on extensions

Use `match_extensions` parameter to specify the extensions (as a dict) to reply to.

Matching is performed on equality for each provided extension.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_extensions_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_extensions={'test': 'value'})

    with httpx.Client() as client:
        response = client.get("https://test_url", extensions={"test": "value"})
```

##### Matching on HTTP timeout(s)

Use `match_extensions` parameter to specify the timeouts (as a dict) to reply to.

Matching is performed on the full timeout dict equality.

```python
import httpx
from pytest_httpx import HTTPXMock


def test_timeout_matching(httpx_mock: HTTPXMock):
    httpx_mock.add_response(match_extensions={'timeout': {'connect': 10, 'read': 10, 'write': 10, 'pool': 10}})

    with httpx.Client() as client:
        response = client.get("https://test_url", timeout=10)
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

Use `stream` parameter (as `httpx.SyncByteStream` or `httpx.AsyncByteStream`) to stream chunks that you specify.

Note that `pytest_httpx.IteratorStream` can be used to provide an iterable.

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

Use the httpx `MultipartStream` via the `stream` parameter to send a multipart response.

Reach out to `httpx` developers if you need this publicly exposed as [this is not a standard use case](https://github.com/encode/httpx/issues/872#issuecomment-633584819).

```python
import httpx
from httpx._multipart import MultipartStream
from pytest_httpx import HTTPXMock


def test_multipart_body(httpx_mock: HTTPXMock):
    httpx_mock.add_response(stream=MultipartStream(data={"key1": "value1"}, files={"file1": b"content of file 1"}, boundary=b"2256d3a36d2a61a1eba35a22bee5c74a"))

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

Use `status_code` parameter to specify the HTTP status code (as an int) of the response.

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

Any valid httpx headers type is supported, you can submit headers as a dict (str or bytes), a list of 2-tuples (str or bytes) or a [`httpx.Header`](https://www.python-httpx.org/api/#headers) instance.

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

Use `http_version` parameter to specify the HTTP protocol version (as a string) of the response.

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

If all callbacks are not executed during test execution, the test case will fail at teardown [(unless you turned `assert_all_responses_were_requested` option off)](#allow-to-register-more-responses-than-what-will-be-requested).

Note that callbacks are considered as responses, and thus are [selected the same way](#how-response-is-selected).
Meaning that you can transpose `httpx_mock.add_response` calls in the related examples into `httpx_mock.add_callback`.

### Dynamic responses

Callback should return a [`httpx.Response`](https://www.python-httpx.org/api/#response) instance.

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

Alternatively, callbacks can also be asynchronous.

As in the following sample simulating network latency on some responses only.

```python
import asyncio
import httpx
import pytest
from pytest_httpx import HTTPXMock


@pytest.mark.asyncio
async def test_dynamic_async_response(httpx_mock: HTTPXMock):
    async def simulate_network_latency(request: httpx.Request):
        await asyncio.sleep(1)
        return httpx.Response(
            status_code=200, json={"url": str(request.url)},
        )

    httpx_mock.add_callback(simulate_network_latency)
    httpx_mock.add_response()

    async with httpx.AsyncClient() as client:
        responses = await asyncio.gather(
            # Response will be received after one second
            client.get("https://test_url"),
            # Response will instantly be received (1 second before the first request)
            client.get("https://test_url")
        )

```

### Raising exceptions

You can simulate HTTPX exception throwing by raising an exception in your callback or use `httpx_mock.add_exception` with the exception instance.

This can be useful if you want to assert that your code handles HTTPX exceptions properly.

```python
import httpx
import pytest
from pytest_httpx import HTTPXMock


def test_exception_raising(httpx_mock: HTTPXMock):
    httpx_mock.add_exception(httpx.ReadTimeout("Unable to read within timeout"))
    
    with httpx.Client() as client:
        with pytest.raises(httpx.ReadTimeout):
            client.get("https://test_url")

```

#### In case no response can be found

The default behavior is to instantly raise a [`httpx.TimeoutException`](https://www.python-httpx.org/advanced/timeouts/) in case no matching response can be found.

The exception message will display the request and every registered responses to help you identify any possible mismatch.

```python
import httpx
import pytest
from pytest_httpx import HTTPXMock


@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
def test_timeout(httpx_mock: HTTPXMock):
    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException):
            client.get("https://test_url")

```

## Check sent requests

The best way to ensure the content of your requests is still to use the `match_headers` and / or `match_content` parameters when adding a response.
In the same spirit, ensuring that no request was issued does not necessarily require any code [(unless you turned `assert_all_requests_were_expected` option off)](#allow-to-not-register-responses-for-every-request).

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

Note that requests are [selected the same way as responses](#how-response-is-selected).
Meaning that you can transpose `httpx_mock.add_response` calls in the related examples into `httpx_mock.get_requests` or `httpx_mock.get_request`.

## Configuring httpx_mock

The `httpx_mock` marker is available and can be used to change the default behavior of the `httpx_mock` fixture.

Refer to [available options](#available-options) for an exhaustive list of options that can be set [per test](#per-test), [per module](#per-module) or even [on the whole test suite](#for-the-whole-test-suite).

### Per test

```python
import pytest

@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_something(httpx_mock):
    ...
```

### Per module

```python
import pytest

pytestmark = pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
```

### For the whole test suite

This should be set in the root `conftest.py` file.
```python
import pytest

def pytest_collection_modifyitems(session, config, items):
    for item in items:
        item.add_marker(pytest.mark.httpx_mock(assert_all_responses_were_requested=False))
```

> [!IMPORTANT]  
> Note that [there currently is a bug in pytest](https://github.com/pytest-dev/pytest/issues/10406) where `pytest_collection_modifyitems` will actually add the marker AFTER its `module` and `class` registration.
> 
> Meaning the order is currently:
> module -> class -> test suite -> test
> 
> instead of:
> test suite -> module -> class -> test

### Available options

#### Allow to register more responses than what will be requested

By default, `pytest-httpx` will ensure that every response was requested during test execution.

If you want to add an optional response, you can use the `is_optional` parameter when [registering a response](#add-responses) or [a callback](#add-callbacks).

```python
def test_fewer_requests_than_expected(httpx_mock):
    # Even if this response never received a corresponding request, the test will not fail at teardown
    httpx_mock.add_response(is_optional=True)
```

If you don't have control over the response registration process (shared fixtures), 
and you want to allow fewer requests than what you registered responses for, 
you can use the `httpx_mock` marker `assert_all_responses_were_requested` option.

> [!CAUTION]
> Use this option at your own risk of not spotting regression (requests not sent) in your code base!

```python
import pytest

@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_fewer_requests_than_expected(httpx_mock):
    # Even if this response never received a corresponding request, the test will not fail at teardown
    httpx_mock.add_response()
```

Note that the `is_optional` parameter will take precedence over the `assert_all_responses_were_requested` option.
Meaning you can still register a response that will be checked for execution at teardown even if `assert_all_responses_were_requested` was set to `False`.

```python
import pytest

@pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
def test_force_expected_request(httpx_mock):
    # Even if the assert_all_responses_were_requested option is set, the test will fail at teardown if this is not matched
    httpx_mock.add_response(is_optional=False)
```

#### Allow to not register responses for every request

By default, `pytest-httpx` will ensure that every request that was issued was expected.

You can use the `httpx_mock` marker `assert_all_requests_were_expected` option to allow more requests than what you registered responses for.

> [!CAUTION]
> Use this option at your own risk of not spotting regression (unexpected requests) in your code base!

```python
import pytest
import httpx

@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
def test_more_requests_than_expected(httpx_mock):
    with httpx.Client() as client:
        # Even if this request was not expected, the test will not fail at teardown
        with pytest.raises(httpx.TimeoutException):
            client.get("https://test_url")
```

#### Allow to register a response for more than one request

By default, `pytest-httpx` will ensure that every request that was issued was expected.

If you want to add a response once, while allowing it to match more than once, you can use the `is_reusable` parameter when [registering a response](#add-responses) or [a callback](#add-callbacks).

```python
import httpx

def test_more_requests_than_responses(httpx_mock):
    httpx_mock.add_response(is_reusable=True)
    with httpx.Client() as client:
        client.get("https://test_url")
        # Even if only one response was registered, the test will not fail at teardown as this request will also be matched
        client.get("https://test_url")
```

If you don't have control over the response registration process (shared fixtures), 
and you want to allow multiple requests to match the same registered response, 
you can use the `httpx_mock` marker `can_send_already_matched_responses` option.

With this option, in case all matching responses have been sent at least once, the last one (according to the registration order) will be sent.

> [!CAUTION]
> Use this option at your own risk of not spotting regression (requests issued more than the expected number of times) in your code base!

```python
import pytest
import httpx

@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_more_requests_than_responses(httpx_mock):
    httpx_mock.add_response()
    with httpx.Client() as client:
        client.get("https://test_url")
        # Even if only one response was registered, the test will not fail at teardown as this request will also be matched
        client.get("https://test_url")
```

#### Do not mock some requests

By default, `pytest-httpx` will mock every request.

But, for instance, in case you want to write integration tests with other servers, you might want to let some requests go through.

To do so, you can use the `httpx_mock` marker `should_mock` option and provide a callable expecting the [`httpx.Request`](https://www.python-httpx.org/api/#request) as parameter and returning a boolean.

Returning `True` will ensure that the request is handled by `pytest-httpx` (mocked), `False` will let the request pass through (not mocked).

```python
import pytest
import httpx

@pytest.mark.httpx_mock(should_mock=lambda request: request.url.host != "www.my_local_test_host")
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
