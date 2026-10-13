import pytest

try:
    import httpx
    import httpx2
except ModuleNotFoundError:
    # If one of the modules isn't installed, there's no sense running these tests.
    pytest.skip(
        allow_module_level=True, reason="One of http/httpx2 modules is missing."
    )

from pytest_httpx import HTTPXMock, get_backends


def test_two_backends_two_names() -> None:
    backends = get_backends()
    names = {backend.name for backend in backends}

    assert names == {"httpx", "httpx2"}


def test_two_backends_are_different() -> None:
    backends = get_backends()
    modules = {id(backend.httpx) for backend in backends}

    assert len(modules) == 2


def test_single_add_response_mocks_both_backends(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(text="hello", is_reusable=True)

    with httpx.Client() as client:
        httpx_response = client.get("https://test_url")

    with httpx2.Client() as client:
        httpx2_response = client.get("https://test_url")

    assert httpx_response.text == "hello"
    assert httpx2_response.text == "hello"


@pytest.mark.asyncio
async def test_single_add_response_mocks_both_async_backends(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(text="async hello", is_reusable=True)

    async with httpx.AsyncClient() as client:
        httpx_response = await client.get("https://test_url")

    async with httpx2.AsyncClient() as client:
        httpx2_response = await client.get("https://test_url")

    assert httpx_response.text == "async hello"
    assert httpx2_response.text == "async hello"


def test_response_type_matches_backend(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(is_reusable=True)

    with httpx.Client() as client:
        httpx_response = client.get("https://test_url")

    with httpx2.Client() as client:
        httpx2_response = client.get("https://test_url")

    # Each response must be an instance of its own backend's Response type.
    assert isinstance(httpx_response, httpx.Response)
    assert not isinstance(httpx_response, httpx2.Response)

    assert isinstance(httpx2_response, httpx2.Response)
    assert not isinstance(httpx2_response, httpx.Response)


def test_requests_from_both_backends_are_retrieved(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(is_reusable=True)

    with httpx.Client() as client:
        client.get("https://httpx_url")

    with httpx2.Client() as client:
        client.options("https://httpx2_url")

    all_requests = httpx_mock.get_requests()

    assert len(all_requests) == 2

    httpx_request = httpx_mock.get_request(url="https://httpx_url")

    assert httpx_request
    assert httpx_request.method == "GET"

    httpx2_request = httpx_mock.get_request(url="https://httpx2_url")

    assert httpx2_request
    assert httpx2_request.method == "OPTIONS"


def test_responses_matched_in_registration_order(
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(text="first")
    httpx_mock.add_response(text="second")

    with httpx.Client() as client:
        first_response = client.get("https://test_url")

    with httpx2.Client() as client:
        second_response = client.get("https://test_url")

    assert first_response.text == "first"
    assert second_response.text == "second"


def test_add_exception_raises_matching_backend_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_exception(
        httpx.ReadTimeout("HTTPX timeout"), url="https://httpx_url"
    )
    httpx_mock.add_exception(
        httpx2.ReadTimeout("HTTPX2 timeout"), url="https://httpx2_url"
    )

    with httpx.Client() as client, pytest.raises(httpx.ReadTimeout) as httpx_exc:
        client.get("https://httpx_url")

    assert str(httpx_exc.value) == "HTTPX timeout"
    assert httpx_exc.value.request.url == httpx.URL("https://httpx_url")

    with httpx2.Client() as client, pytest.raises(httpx2.ReadTimeout) as httpx2_exc:
        client.get("https://httpx2_url")

    assert str(httpx2_exc.value) == "HTTPX2 timeout"
    assert httpx2_exc.value.request.url == httpx2.URL("https://httpx2_url")


seen_request_modules: set[str] = set()


def _should_mock(request: httpx.Request | httpx2.Request) -> bool:
    # Record the module of the request object so the test below could check them.
    match type(request):
        case httpx.Request:
            seen_request_modules.add("httpx")
        case httpx2.Request:
            seen_request_modules.add("httpx2")

    return True


@pytest.mark.httpx_mock(should_mock=_should_mock)
def test_should_mock_used_by_both_backends(httpx_mock: HTTPXMock) -> None:
    seen_request_modules.clear()
    httpx_mock.add_response(is_reusable=True)

    with httpx.Client() as client:
        client.get("https://test_url")

    with httpx2.Client() as client:
        client.get("https://test_url")

    assert set(seen_request_modules) == {"httpx", "httpx2"}


def test_conflicting_params_backend_agnostic(httpx_mock: HTTPXMock) -> None:
    with pytest.raises(ValueError) as exc_httpx:
        httpx_mock.add_response(
            url=httpx.URL("https://test_url?a=1"), match_params={"a": "1"}
        )

    with pytest.raises(ValueError) as exc_httpx2:
        httpx_mock.add_response(
            url=httpx2.URL("https://test_url?a=1"), match_params={"a": "1"}
        )

    assert (
        str(exc_httpx.value)
        == str(exc_httpx2.value)
        == "Provided URL must not contain any query parameter when match_params is used."
    )
