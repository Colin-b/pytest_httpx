# see https://docs.pytest.org/en/documentation-restructure/how-to/writing_plugins.html#testing-plugins
import pytest

from pytest_httpx import HTTPXBackend, get_backends

pytest_plugins = ["pytester"]


@pytest.fixture(params=get_backends(), ids=lambda b: b.name)
def backend(request: pytest.FixtureRequest) -> HTTPXBackend:
    return request.param


@pytest.fixture
def plugin_tests_conftest(testdir: pytest.Testdir) -> None:
    testdir.makeconftest("""
        import pytest
        from pytest_httpx import get_backends

        @pytest.fixture(params=get_backends(), ids=lambda b: b.name)
        def backend(request):
            return request.param
        """)
