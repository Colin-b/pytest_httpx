from typing import List, Dict, Union

import httpx
import pytest
from httpx import Request, Response, Timeout, URL
from httpx.content_streams import ByteStream
from httpx.dispatch.base import SyncDispatcher


def _url(url: Union[str, URL]) -> URL:
    return URL(url) if isinstance(url, str) else url


class HTTPXMock:
    def __init__(self):
        self.requests: List[Request] = []
        self.responses: Dict[str, List[Response]] = {}

    def add_response(self, url: Union[str, URL], method: str = "GET", status_code: int = 200, http_version: str = "HTTP/1.1", headers: dict = None, content: bytes=b""):
        """

        :param url:
        :param method:
        :param status_code:
        :param http_version:
        :param headers:
        :param content:
        """
        # TODO Allow non strict URL params checking
        # TODO Allow to provide JSON as python
        # TODO Allow to provide files
        # TODO Allow to retrieve requests
        # TODO Allow to send without body?
        self.responses.setdefault((method, _url(url)), []).append(Response(
            status_code=status_code,
            http_version=http_version,
            headers=list(headers.items()) if headers else [],
            stream=ByteStream(content),
            request=None,  # Will be set upon reception of the actual request
        ))

    def _get_response(self, request: Request) -> Response:
        responses = self.responses.get((request.method, request.url))
        if not responses:
            raise Exception(f"No mock can be found for {request.method} request on {request.url}.")
        if len(responses) > 1:
            response = responses.pop(0)
        else:
            response = responses[0]
        response.request = request
        response.called = True
        return response

    def _assert_everything_called(self):
        non_called_responses = {}
        for (method, url), responses in self.responses.items():
            for response in responses:
                if not hasattr(response, "called"):
                    non_called_responses.setdefault((method, url), []).append(response)
        self.responses.clear()
        assert not non_called_responses, f"The following responses are mocked but not requested: {non_called_responses}"


class _PytestSyncDispatcher(SyncDispatcher):
    def __init__(self, mock: HTTPXMock):
        self.mock = mock

    def send(self, request: Request, timeout: Timeout = None) -> Response:
        return self.mock._get_response(request)


@pytest.fixture
def httpx_mock(monkeypatch) -> HTTPXMock:
    mock = HTTPXMock()
    # TODO Handle Async
    monkeypatch.setattr(httpx.client.Client, "dispatcher_for_url", lambda self, url: _PytestSyncDispatcher(mock))
    yield mock
    mock._assert_everything_called()
