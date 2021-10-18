# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.20.\*

## [0.13.0] - 2021-08-19
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.19.\*
- `files` parameter of `httpx_mock.add_response` now expect dictionary values to be binary (as per [httpx new requirement](https://github.com/encode/httpx/blob/master/CHANGELOG.md#0190-19th-june-2021)).

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
- Order of different parameters does not matters anymore for URL matching. It does however still matter for a same parameter.

## [0.10.0] - 2020-10-06
### Added
- Document how to assert that no requests were issued.
- Document how to send cookies.
- Explicit support for python 3.9

### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.16.*
- Update documentation to reflect the latest way of sending bytes using `httpx`. Via `content` parameter instead of `data`.
- Code now follow `black==20.8b1` formatting instead of the git master version.
- Sending a JSON response using `json` parameter will now set the `application/json` content-type header by default.

### Fixed
- Allow to provide any supported `httpx` headers type in headers parameter for `httpx_mock.add_response` and `pytest_httpx.to_response`. Previously only dict was supported.

## [0.9.0] - 2020-09-22
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.15.*
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
- Requires [`httpx`](https://www.python-httpx.org)==0.14.*

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
- Requires [`httpx`](https://www.python-httpx.org)==0.13.*
- requires [`pytest`](https://docs.pytest.org/en/latest/) 5.4.0 (at least)
- callbacks must now return a tuple as per `httpcore` specifications. Refer to documentation for more details.
- callbacks timeout parameter is now a dict as per `httpcore` specifications.

## [0.2.1] - 2020-03-20
### Fixed
- Handle the fact that some classes and functions we use are now part of internals within [`httpx`](https://www.python-httpx.org).

## [0.2.0] - 2020-03-09
### Changed
- Requires [`httpx`](https://www.python-httpx.org)==0.12.*

## [0.1.0] - 2020-02-13
### Added
- Consider as stable.

## [0.0.5] - 2020-02-10
### Added
- match_headers parameter now allows to match on headers.
- match_content parameter now allows to match on full body.

### Changed
- httpx.HTTPError is now raised instead of Exception in case a request cannot be matched.

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
- Allow to provide JSON response as python values.
- Mock async httpx requests as well.
- Allow to provide files and boundary for multipart response.
- Allow to provide data as a dictionary for multipart response.
- Allow to provide callbacks that are executed upon reception of a request.
- Handle the fact that parameters may be introduced in httpx *Dispatcher.send method.
- Allow to retrieve all matching requests with HTTPXMock.get_requests

### Changed
- method can now be provided even if not entirely upper cased.
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

[Unreleased]: https://github.com/Colin-b/pytest_httpx/compare/v0.13.0...HEAD
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
