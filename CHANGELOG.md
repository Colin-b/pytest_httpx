# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2020-07-31
### Changed
- requires [`pytest`](https://docs.pytest.org/en/latest/) 6.

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

[Unreleased]: https://github.com/Colin-b/pytest_httpx/compare/v0.5.0...HEAD
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
