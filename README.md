<h2 align="center">pytest fixture for HTTPX</h2>

<p align="center">
<a href="https://pypi.org/project/pytest-httpx/"><img alt="pypi version" src="https://img.shields.io/pypi/v/pytest_httpx"></a>
<a href="https://travis-ci.com/Colin-b/pytest_httpx"><img alt="Build status" src="https://api.travis-ci.com/Colin-b/pytest_httpx.svg?branch=master"></a>
<a href="https://travis-ci.com/Colin-b/pytest_httpx"><img alt="Coverage" src="https://img.shields.io/badge/coverage-100%25-brightgreen"></a>
<a href="https://github.com/psf/black"><img alt="Code style: black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://travis-ci.com/Colin-b/pytest_httpx"><img alt="Number of tests" src="https://img.shields.io/badge/tests-10 passed-blue"></a>
<a href="https://pypi.org/project/pytest-httpx/"><img alt="Number of downloads" src="https://img.shields.io/pypi/dm/pytest_httpx"></a>
</p>

This module is still under development and cannot be considered stable.

Use `pytest_httpx.httpx_mock` [`pytest`](https://docs.pytest.org/en/latest/) fixture to mock [`httpx`](https://www.python-httpx.org) requests.


## Add responses

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_something(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")

    response = httpx.get("http://test_url")
```

If all responses are not sent back during test execution, the test case will fail.

## Check sent requests

```python
import httpx
from pytest_httpx import httpx_mock, HTTPXMock


def test_something(httpx_mock: HTTPXMock):
    httpx_mock.add_response("http://test_url")

    response = httpx.get("http://test_url")

    # requests are in httpx_mock.requests
```
