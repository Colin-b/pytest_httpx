# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.31.0] - 2024-09-20
### Changed
- Tests will now fail at teardown by default if some requests were issued but were not matched.
  - This behavior can be changed thanks to the new ``pytest.mark.httpx_mock(assert_all_requests_were_expected=False)`` option.
- The `httpx_mock` fixture is now configured using a marker (many thanks to [`Frazer McLean`](https://github.com/RazerM)).
  ```python
  # Apply marker to whole module
  pytestmark = pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
  
  # Or to specific tests
  @pytest.mark.httpx_mock(non_mocked_hosts=[...])
  def test_foo(httpx_mock):
      ...
  ```
  - The following options are available:
    - `assert_all_responses_were_requested` (boolean), defaulting to `True`.
    - `assert_all_requests_were_expected` (boolean), defaulting to `True`.
    - `non_mocked_hosts` (iterable), defaulting to an empty list, meaning all hosts are mocked.
- `httpx_mock.reset` do not expect any parameter anymore and will only reset the mock state (no assertions will be performed).

### Removed
- `pytest` `7` is not supported anymore (`pytest` `8` has been out for 9 months already).
- `assert_all_responses_were_requested` fixture is not available anymore, use `pytest.mark.httpx_mock(assert_all_responses_were_requested=False)` instead.
- `non_mocked_hosts` fixture is not available anymore, use `pytest.mark.httpx_mock(non_mocked_hosts=[])` instead.

## [0.30.0] - 2024-02-21
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.27.\*

### Fixed
- Switch from `setup.py` to `pyproject.toml` (many thanks to [`Felix Scherz`](https://github.com/felixscherz)).

## [0.29.0] - 2024-01-29
### Added
- Add support for [`pytest`](https://docs.pytest.org)==8.\* ([`pytest`](https://docs.pytest.org)==7.\* is still supported for now) (many thanks to [`Yossi Rozantsev`](https://github.com/Apakottur)).

## [0.28.0] - 2023-12-21
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.26.\*

## [0.27.0] - 2023-11-13
### Added
- Explicit support for python `3.12`.

### Fixed
- Custom HTTP transport are now handled (parent call to `handle_async_request` or `handle_request`).

### Changed
- Only HTTP transport are now mocked, this should not have any impact, however if it does, please feel free to open an issue describing your use case.

## [0.26.0] - 2023-09-18
### Added
- Added `proxy_url` parameter which allows matching on proxy URL.

## [0.25.0] - 2023-09-11
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.25.\*

### Removed
- `pytest` `6` is no longer supported.

## [0.24.0] - 2023-09-04
### Added
- Added `match_json` parameter which allows matching on JSON decoded body (matching against python representation instead of bytes).

### Changed
- Even if it was never documented as a feature, the `match_headers` parameter was not considering header names case when matching.
  - As this might have been considered a feature by some users, the fact that `match_headers` will now respect casing is documented as a breaking change.

### Fixed
- Matching on headers does not ignore name case anymore, the name must now be cased as sent (as some servers might expect a specific case).
- Error message in case a request does not match will now include request headers with mismatching name case as well.
- Error message in case a request does not match will now include request headers when not provided as lower-cased to `match_headers`.
- Add `:Any` type hint to `**matchers` function arguments to satisfy strict type checking mode in [`pyright`](https://microsoft.github.io/pyright/#/).

## [0.23.1] - 2023-08-02
### Fixed
- Version `0.23.0` introduced a regression removing the support for mutating json content provided in `httpx_mock.add_response`. 
  - This is fixed, you can now expect the JSON return being as it was when provided to `httpx_mock.add_response`:
```python
    mutating_json = {"content": "request 1"}
    # This will return {"content": "request 1"}
    httpx_mock.add_response(json=mutating_json)

    mutating_json["content"] = "request 2"
    # This will return {"content": "request 2"}
    httpx_mock.add_response(json=mutating_json)
```

## [0.23.0] - 2023-08-02
### Removed
- Python `3.7` and `3.8` are no longer supported.

### Fixed
- `httpx_mock.add_response` is now returning a new `httpx.Response` instance upon each matching request. Preventing unnecessary recursion in streams.

## [0.22.0] - 2023-04-12
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.24.\*

## [0.21.3] - 2023-01-20
### Fixed
- Update version specifiers for `pytest` dependency to support `packaging` `23`.
- Add explicit support for `python` `3.11`.

## [0.21.2] - 2022-11-03
### Fixed
- URL containing non ASCII characters in query can now be matched.
- Requests are now cleared when calling `httpx_mock.reset`.

## [0.21.1] - 2022-10-20
### Fixed
- `httpx_mock.add_callback` now handles async callbacks.

## [0.21.0] - 2022-05-24
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.23.\*

### Removed
- Python `3.6` is no longer supported.

## [0.20.0] - 2022-02-05
### Added
- Add support for [`pytest`](https://docs.pytest.org)==7.\* ([`pytest`](https://docs.pytest.org)==6.\* is still supported for now) (many thanks to [`Craig Blaszczyk`](https://github.com/jakul)).

## [0.19.0] - 2022-01-26
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.22.\*

### Deprecated
- Python 3.6 is no longer supported.

## [0.18.0] - 2022-01-17
### Fixed
- Callback are now executed as expected when there is a matching already sent response.

### Changed
- Registration order is now looking at responses and callbacks. Prior to this version, registration order was looking at responses before callbacks.

### Removed
- `httpx_mock.add_response` `data`, `files` and `boundary` parameters have been removed. It was deprecated since `0.17.0`. Refer to this version changelog entry for more details on how to update your code.

## [0.17.3] - 2021-12-27
### Fixed
- A callback can now raise an exception again (regression in mypy check since [0.16.0]).

### Added
- An exception can now be raised without creating a callback by using `httpx_mock.add_exception` method.

## [0.17.2] - 2021-12-23
### Fixed
- Do not consider a callback response as read, even if it is not a stream, before returning to `httpx`. Allowing any specific httpx handling to be triggered such as `httpx.Response.elapsed` computing.

## [0.17.1] - 2021-12-20
### Fixed
- Do not consider a response as read, even if it is not a stream, before returning to `httpx`. Allowing any specific httpx handling to be triggered such as `httpx.Response.elapsed` computing.

## [0.17.0] - 2021-12-20
### Changed
- `httpx_mock.add_response` `data` parameter is only used for multipart content. It was deprecated since `0.14.0`. Refer to this version changelog entry for more details on how to update your code.

### Removed
- `pytest_httpx.to_response` function has been removed. It was deprecated since `0.14.0`. Refer to this version changelog entry for more details on how to update your code.

### Deprecated
- `httpx_mock.add_response` `data`, `files` and `boundary` parameters that were only used for multipart content. Instead, provide the `stream` parameter with an instance of the `httpx._multipart.MultipartStream`.

### Fixed
- Responses are no more read or closed when returned to the client. Allowing to add a response once and reading it as a new response on every request.

## [0.16.0] - 2021-12-20
### Changed
- Callbacks are now expected to have a single parameter, the request. The previously second parameter `extensions`, can still be accessed via `request.extensions`.

### Fixed
- Allow for users to run `mypy --strict`.

## [0.15.0] - 2021-11-16
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.21.\*

## [0.14.0] - 2021-10-22
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.20.\*  (many thanks to [`Terence Honles`](https://github.com/terencehonles))
- Callbacks are now expected to return a `httpx.Response` instance instead of the previous `httpcore.Response` tuple. As a consequence, `pytest_httpx.to_response` now returns a `httpx.Response` instance.

### Added
- `httpx_mock.add_response` now allows to explicitly provide bytes using `content` parameter.
- `httpx_mock.add_response` now allows to explicitly provide string using `text` parameter.
- `httpx_mock.add_response` now allows to explicitly provide HTML string content using `html` parameter.
- `httpx_mock.add_response` now allows to explicitly provide streamed content using `stream` parameter and the new `pytest_httpx.IteratorStream` class.

### Deprecated
- `pytest_httpx.to_response` is now deprecated in favor of `httpx.Response`. This function will be removed in a future release.
- `httpx_mock.add_response` `data` parameter should now only be used for multipart content. Instead, use the appropriate parameter amongst `content`, `text`, `html` or `stream`.

## [0.13.0] - 2021-08-19
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.19.\*
- `files` parameter of `httpx_mock.add_response` now expect dictionary values to be binary (as per [`httpx` new requirement](https://github.com/encode/httpx/blob/master/CHANGELOG.md#0190-19th-june-2021)).

## [0.12.1] - 2021-08-11
### Fixed
- Type information is now provided following [PEP 561](https://www.python.org/dev/peps/pep-0561/) (many thanks to [`Caleb Ho`](https://github.com/calebho)).

## [0.12.0] - 2021-04-27
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.18.\*
- `ext` callback parameter was renamed into `extensions`.

## [0.11.0] - 2021-03-01
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.17.\*

## [0.10.1] - 2020-11-25
### Fixed
- Order of different parameters does not matter anymore for URL matching. It does however still matter for a same parameter.

## [0.10.0] - 2020-10-06
### Added
- Document how to assert that no requests were issued.
- Document how to send cookies.
- Explicit support for python 3.9

### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.16.\*
- Update documentation to reflect the latest way of sending bytes using `httpx`. Via `content` parameter instead of `data`.
- Code now follow `black==20.8b1` formatting instead of the git master version.
- Sending a JSON response using `json` parameter will now set the `application/json` content-type header by default.

### Fixed
- Allow to provide any supported `httpx` headers type in headers parameter for `httpx_mock.add_response` and `pytest_httpx.to_response`. Previously only dict was supported.

## [0.9.0] - 2020-09-22
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.15.\*
- Callbacks are now called with `ext` dictionary instead of `timeout`. To follow `httpcore` design changes. You can still retrieve timeout by using ```ext['timeout']```

## [0.8.0] - 2020-08-26
### Added
- `non_mocked_hosts` fixture allowing to avoid mocking requests sent on some specific hosts.

### Changed
- Display the matchers that were not matched instead of the responses that were not sent.

## [0.7.0] - 2020-08-13
### Changed
- The `httpx.HTTPError` message issued in case no mock could be found is now a `httpx.TimeoutException` containing all information required to fix the test case (if needed).

## [0.6.0] - 2020-08-07
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.14.\*

## [0.5.0] - 2020-07-31
### Changed
- requires [`pytest`](https://docs.pytest.org/en/latest/) 6.
- `assert_and_reset` mock method has been renamed to `reset` and now takes a boolean parameter to specify if assertion should be performed.

### Added
- It is now possible to disable the assertion that all registered responses were requested thanks to the `assert_all_responses_were_requested` fixture. Refer to documentation for more details.

### Removed
- It is not possible to provide an URL encoded response anymore by providing a dictionary in `data` parameter.

## [0.4.0] - 2020-06-05
### Changed
- `httpx_mock` [`pytest`](https://docs.pytest.org/en/latest/) fixture does not need to be explicitly imported anymore (many thanks to [`Thomas LÉVEIL`](https://github.com/thomasleveil)).

## [0.3.0] - 2020-05-24
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.13.\*
- requires [`pytest`](https://docs.pytest.org/en/latest/) 5.4.0 (at least)
- callbacks must now return a tuple as per `httpcore` specifications. Refer to documentation for more details.
- callbacks timeout parameter is now a dict as per `httpcore` specifications.

## [0.2.1] - 2020-03-20
### Fixed
- Handle the fact that some classes and functions we use are now part of internals within [`httpx`](https://www.python-httpx.org).

## [0.2.0] - 2020-03-09
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.12.\*

## [0.1.0] - 2020-02-13
### Added
- Consider as stable.

## [0.0.5] - 2020-02-10
### Added
- match_headers parameter now allows matching on headers.
- match_content parameter now allows matching on full body.

### Changed
- `httpx.HTTPError` is now raised instead of `Exception` in case a request cannot be matched.

## [0.0.4] - 2020-02-07
### Changed
- url is not a mandatory parameter for response registration anymore.
- url is not a mandatory parameter for callback registration anymore.
- url is not a mandatory parameter for request retrieval anymore.
- method does not have a default value for response registration anymore.
- method does not have a default value for callback registration anymore.
- method does not have a default value for request retrieval anymore.
- url and methods are not positional arguments anymore.

## [0.0.3] - 2020-02-06
### Added
- Allow providing JSON response as python values.
- Mock async `httpx` requests as well.
- Allow providing files and boundary for multipart response.
- Allow to provide data as a dictionary for multipart response.
- Allow providing callbacks that are executed upon reception of a request.
- Handle the fact that parameters may be introduced in `httpx` *Dispatcher.send method.
- Allow to retrieve all matching requests with HTTPXMock.get_requests

### Changed
- method can now be provided even if not entirely upper-cased.
- content parameter renamed into data.
- HTTPXMock.get_request now fails if more than one request match. Use HTTPXMock.get_request instead.
- HTTPXMock.requests is now private, use HTTPXMock.get_requests instead.
- HTTPXMock.responses is now private, it should not be accessed anyway.
- url can now be a re.Pattern instance.

## [0.0.2] - 2020-02-06
### Added
- Allow to retrieve requests.

## [0.0.1] - 2020-02-05
### Added
- First release, should be considered as unstable for now as design might change.

[Unreleased]: https://github.com/Colin-b/pytest_httpx/compare/v0.31.0...HEAD
[0.31.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.30.0...v0.31.0
[0.30.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.29.0...v0.30.0
[0.29.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.28.0...v0.29.0
[0.28.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.27.0...v0.28.0
[0.27.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.26.0...v0.27.0
[0.26.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.25.0...v0.26.0
[0.25.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.24.0...v0.25.0
[0.24.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.23.1...v0.24.0
[0.23.1]: https://github.com/Colin-b/pytest_httpx/compare/v0.23.0...v0.23.1
[0.23.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.22.0...v0.23.0
[0.22.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.21.3...v0.22.0
[0.21.3]: https://github.com/Colin-b/pytest_httpx/compare/v0.21.2...v0.21.3
[0.21.2]: https://github.com/Colin-b/pytest_httpx/compare/v0.21.1...v0.21.2
[0.21.1]: https://github.com/Colin-b/pytest_httpx/compare/v0.21.0...v0.21.1
[0.21.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.20.0...v0.21.0
[0.20.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.19.0...v0.20.0
[0.19.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.18.0...v0.19.0
[0.18.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.17.3...v0.18.0
[0.17.3]: https://github.com/Colin-b/pytest_httpx/compare/v0.17.2...v0.17.3
[0.17.2]: https://github.com/Colin-b/pytest_httpx/compare/v0.17.1...v0.17.2
[0.17.1]: https://github.com/Colin-b/pytest_httpx/compare/v0.17.0...v0.17.1
[0.17.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.16.0...v0.17.0
[0.16.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.15.0...v0.16.0
[0.15.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.14.0...v0.15.0
[0.14.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.13.0...v0.14.0
[0.13.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.12.1...v0.13.0
[0.12.1]: https://github.com/Colin-b/pytest_httpx/compare/v0.12.0...v0.12.1
[0.12.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.10.1...v0.11.0
[0.10.1]: https://github.com/Colin-b/pytest_httpx/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.9.0...v0.10.0
[0.9.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.8.0...v0.9.0
[0.8.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/Colin-b/pytest_httpx/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Colin-b/pytest_httpx/compare/v0.0.5...v0.1.0
[0.0.5]: https://github.com/Colin-b/pytest_httpx/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/Colin-b/pytest_httpx/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/Colin-b/pytest_httpx/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/Colin-b/pytest_httpx/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/Colin-b/pytest_httpx/releases/tag/v0.0.1
