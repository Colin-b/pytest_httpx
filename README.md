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
