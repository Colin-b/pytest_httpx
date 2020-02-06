# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changed
- url is not a mandatory parameter for response registration anymore.
- url is not a mandatory parameter for callback registration anymore.
- url is not a mandatory parameter for request retrieval anymore.
- method does not have a default value for response registration anymore.
- method does not have a default value for callback registration anymore.
- method does not have a default value for request retrieval anymore.

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

[Unreleased]: https://github.com/Colin-b/pytest_httpx/compare/v0.0.3...HEAD
[0.0.3]: https://github.com/Colin-b/pytest_httpx/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/Colin-b/pytest_httpx/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/Colin-b/pytest_httpx/releases/tag/v0.0.1
