from pytest import Testdir


def test_fixture_is_available(testdir: Testdir) -> None:
    # create a temporary pytest test file
    testdir.makepyfile(
        """
        import httpx
        
        
        def test_http(httpx_mock):
            mock = httpx_mock.add_response(url="https://foo.tld")
            r = httpx.get("https://foo.tld")
            assert httpx_mock.get_request() is not None

    """
    )

    # run all tests with pytest
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_httpx_mock_unused_response(testdir: Testdir) -> None:
    """
    Unused responses should fail test case.
    """
    testdir.makepyfile(
        """
        def test_httpx_mock_unused_response(httpx_mock):
            httpx_mock.add_response()
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*Match all requests",
        ]
    )


def test_httpx_mock_unused_response_without_assertion(testdir: Testdir) -> None:
    """
    Unused responses should not fail test case if
    assert_all_responses_were_requested option is set to False.
    """
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
        def test_httpx_mock_unused_response_without_assertion(httpx_mock):
            httpx_mock.add_response()
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_httpx_mock_unused_callback(testdir: Testdir) -> None:
    """
    Unused callbacks should fail test case.
    """
    testdir.makepyfile(
        """
        def test_httpx_mock_unused_callback(httpx_mock):
            def unused(*args, **kwargs):
                pass
        
            httpx_mock.add_callback(unused)

    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*Match all requests",
        ]
    )


def test_httpx_mock_unused_callback_without_assertion(testdir: Testdir) -> None:
    """
    Unused callbacks should not fail test case if
    assert_all_responses_were_requested option is set to False.
    """
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
        def test_httpx_mock_unused_callback_without_assertion(httpx_mock):
            def unused(*args, **kwargs):
                pass
        
            httpx_mock.add_callback(unused)

    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_httpx_mock_unexpected_request(testdir: Testdir) -> None:
    """
    Unexpected request should fail test case if
    assert_all_requests_were_expected option is set to True (default).
    """
    testdir.makepyfile(
        """
        import httpx
        import pytest

        def test_httpx_mock_unexpected_request(httpx_mock):
            with httpx.Client() as client:
                # Non mocked request
                with pytest.raises(httpx.TimeoutException):
                    client.get("https://foo.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following requests were not expected:",
            "*[<Request('GET', 'https://foo.tld')>]",
        ]
    )


def test_httpx_mock_unexpected_request_without_assertion(testdir: Testdir) -> None:
    """
    Unexpected request should not fail test case if
    assert_all_requests_were_expected option is set to False.
    """
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.mark.httpx_mock(assert_all_requests_were_expected=False)
        def test_httpx_mock_unexpected_request(httpx_mock):
            with httpx.Client() as client:
                # Non mocked request
                with pytest.raises(httpx.TimeoutException):
                    client.get("https://foo.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_httpx_mock_non_mocked_hosts_sync(testdir: Testdir) -> None:
    """
    Non mocked hosts should go through while other requests should be mocked.
    """
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.mark.httpx_mock(non_mocked_hosts=["localhost"])
        def test_httpx_mock_non_mocked_hosts_sync(httpx_mock):
            httpx_mock.add_response()
            
            with httpx.Client() as client:
                # Mocked request
                client.get("https://foo.tld")
            
                # Non mocked request
                with pytest.raises(httpx.ConnectError):
                    client.get("https://localhost:5005")
            
            # Assert that a single request was mocked
            assert len(httpx_mock.get_requests()) == 1
            
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_httpx_mock_non_mocked_hosts_async(testdir: Testdir) -> None:
    """
    Non mocked hosts should go through while other requests should be mocked.
    """
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.mark.asyncio
        @pytest.mark.httpx_mock(non_mocked_hosts=["localhost"])
        async def test_httpx_mock_non_mocked_hosts_async(httpx_mock):
            httpx_mock.add_response()
            
            async with httpx.AsyncClient() as client:
                # Mocked request
                await client.get("https://foo.tld")
            
                # Non mocked request
                with pytest.raises(httpx.ConnectError):
                    await client.get("https://localhost:5005")
            
            # Assert that a single request was mocked
            assert len(httpx_mock.get_requests()) == 1
            
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_invalid_marker(testdir: Testdir) -> None:
    """
    Unknown marker keyword arguments should raise a TypeError.
    """
    testdir.makepyfile(
        """
        import pytest

        @pytest.mark.httpx_mock(foo=123)
        def test_httpx_mock_non_mocked_hosts_async(httpx_mock):
            pass
            
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.re_match_lines([r".*got an unexpected keyword argument 'foo'"])
