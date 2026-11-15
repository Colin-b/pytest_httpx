import json
import re
from pathlib import Path

import httpx
import pytest

from pytest_httpx import HTTPXMock, IteratorStream


@pytest.mark.parametrize("as_string", [True, False])
@pytest.mark.parametrize("async_client", [True, False])
async def test_response_file(
    httpx_mock: HTTPXMock, tmp_path: Path, as_string, async_client
):
    path = tmp_path / "responses.json"
    path.write_text(
        json.dumps(
            [
                {
                    "url": "https://test_url",
                    "method": "POST",
                    "match_json": {"query": "中文"},
                    "status_code": 201,
                    "http_version": "HTTP/2.0",
                    "headers": [["x-value", "first"], ["x-value", "second"]],
                    "json": {"result": "你好"},
                },
                {"url": "https://test_url", "text": "second"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    httpx_mock.add_response(url="https://before", text="before")
    httpx_mock.add_responses_from_file(str(path) if as_string else path)
    path.unlink()  # The file is read at registration, not when requests arrive.
    httpx_mock.add_response(url="https://after", text="after")
    requests = [
        ("GET", "https://before", {}),
        ("POST", "https://test_url", {"json": {"query": "中文"}}),
        ("GET", "https://test_url", {}),
        ("GET", "https://after", {}),
    ]
    if async_client:
        async with httpx.AsyncClient() as client:
            responses = [
                await client.request(method, url, **kwargs)
                for method, url, kwargs in requests
            ]
    else:
        with httpx.Client() as client:
            responses = [
                client.request(method, url, **kwargs)
                for method, url, kwargs in requests
            ]
    assert responses[0].text == "before"
    assert responses[1].status_code == 201
    assert responses[1].http_version == "HTTP/2.0"
    assert responses[1].headers.get_list("x-value") == ["first", "second"]
    assert responses[1].json() == {"result": "你好"}
    assert responses[2].text == "second"
    assert responses[3].text == "after"


@pytest.mark.parametrize(
    "body", [{"content": b"\x00\xff"}, {"stream": IteratorStream([b"\x00", b"\xff"])}]
)
def test_python_overrides(httpx_mock: HTTPXMock, tmp_path: Path, body):
    path = tmp_path / "responses.json"
    path.write_text(
        '[{"status_code": 404, "url": "https://unused"}, {"status_code": 503}]',
        encoding="utf-8",
    )
    httpx_mock.add_responses_from_file(
        path,
        status_code=202,
        url=re.compile("https://test.*"),
        match_content=b"\xff",
        **body,
    )
    with httpx.Client() as client:
        for url in ("https://test_one", "https://test_two"):
            response = client.post(url, content=b"\xff")
            assert response.status_code == 202
            assert response.content == b"\x00\xff"


def test_optional_and_reusable(httpx_mock: HTTPXMock, tmp_path: Path):
    path = tmp_path / "responses.json"
    path.write_text(
        '[{"url": "https://unused", "is_optional": true}, {"url": "https://test_url", "is_reusable": true}]',
        encoding="utf-8",
    )
    httpx_mock.add_responses_from_file(path)
    with httpx.Client() as client:
        for _ in range(2):
            assert client.get("https://test_url").status_code == 200


@pytest.mark.parametrize(
    "document", ["{}", "null", '"text"', "1", "[{}, null]", "[{}, []]", "[{}, 1]"]
)
def test_invalid_structure(httpx_mock: HTTPXMock, tmp_path: Path, document):
    path = tmp_path / "responses.json"
    path.write_text(document, encoding="utf-8")
    with pytest.raises(ValueError, match="JSON array of objects"):
        httpx_mock.add_responses_from_file(path)
    assert httpx_mock._callbacks == []


def test_invalid_matcher_is_atomic(httpx_mock: HTTPXMock, tmp_path: Path):
    httpx_mock.add_response(text="existing")
    path = tmp_path / "responses.json"
    path.write_text('[{}, {"unknown_matcher": true}]', encoding="utf-8")
    with pytest.raises(TypeError, match="unknown_matcher"):
        httpx_mock.add_responses_from_file(path)
    with httpx.Client() as client:
        assert client.get("https://test_url").text == "existing"
    assert len(httpx_mock._callbacks) == 1


def test_empty_file_list(httpx_mock: HTTPXMock, tmp_path: Path):
    path = tmp_path / "responses.json"
    path.write_text("[]", encoding="utf-8")
    httpx_mock.add_responses_from_file(path)
    assert httpx_mock._callbacks == []


@pytest.mark.parametrize(
    "contents, error", [(b"[", json.JSONDecodeError), (b"\xff", UnicodeDecodeError)]
)
def test_unreadable_content(httpx_mock: HTTPXMock, tmp_path: Path, contents, error):
    path = tmp_path / "responses.json"
    path.write_bytes(contents)
    with pytest.raises(error):
        httpx_mock.add_responses_from_file(path)
    assert httpx_mock._callbacks == []


def test_missing_file(httpx_mock: HTTPXMock, tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        httpx_mock.add_responses_from_file(tmp_path / "missing.json")


@pytest.mark.httpx_mock(
    assert_all_responses_were_requested=False, can_send_already_matched_responses=True
)
def test_fixture_defaults(httpx_mock: HTTPXMock, tmp_path: Path):
    path = tmp_path / "responses.json"
    path.write_text(
        '[{"url": "https://unused"}, {"url": "https://test_url"}]', encoding="utf-8"
    )
    httpx_mock.add_responses_from_file(path)
    with httpx.Client() as client:
        for _ in range(2):
            assert client.get("https://test_url").status_code == 200


def test_overrides_replace_mappings(httpx_mock: HTTPXMock, tmp_path: Path):
    path = tmp_path / "responses.json"
    path.write_text(
        '[{"headers": {"x-old": "old"}, "json": {"old": true}}]', encoding="utf-8"
    )
    body = {"nested": ["original"]}
    httpx_mock.add_responses_from_file(path, headers={"x-new": "new"}, json=body)
    body["nested"].append("changed")
    with httpx.Client() as client:
        response = client.get("https://test_url")
    assert response.json() == {"nested": ["original"]}
    assert response.headers["x-new"] == "new"
    assert "x-old" not in response.headers


@pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
def test_unmatched_request_does_not_consume_response(
    httpx_mock: HTTPXMock, tmp_path: Path
):
    path = tmp_path / "responses.json"
    path.write_text(
        '[{"url": "https://test_url", "match_params": {"q": "value"}, "text": "matched"}]',
        encoding="utf-8",
    )
    httpx_mock.add_responses_from_file(path)
    with httpx.Client() as client:
        with pytest.raises(httpx.TimeoutException):
            client.get("https://test_url", params={"q": "other"})
        assert client.get("https://test_url", params={"q": "value"}).text == "matched"
        with pytest.raises(httpx.TimeoutException):
            client.get("https://test_url", params={"q": "value"})
