import httpx

from pytest_httpx import HTTPXMock


class RecordingCallback(list[httpx.Request]):
    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.append(request)
        return httpx.Response(201, text="recorded")


def test_false_valued_callback(httpx_mock: HTTPXMock) -> None:
    callback = RecordingCallback()
    httpx_mock.add_callback(callback)

    with httpx.Client() as client:
        response = client.get("https://test_url")

    assert response.status_code == 201
    assert response.text == "recorded"
    assert callback == [httpx_mock.get_request()]


async def test_false_valued_callback_async_client(httpx_mock: HTTPXMock) -> None:
    callback = RecordingCallback()
    httpx_mock.add_callback(callback)

    async with httpx.AsyncClient() as client:
        response = await client.get("https://test_url")

    assert response.status_code == 201
    assert response.text == "recorded"
    assert callback == [httpx_mock.get_request()]
