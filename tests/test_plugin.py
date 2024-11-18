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
            "*  - Match any request",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-register-more-responses-than-what-will-be-requested",
        ],
        consecutive=True,
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
            "*  - Match any request",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-register-more-responses-than-what-will-be-requested",
        ],
        consecutive=True,
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
            "*  - GET request on https://foo.tld",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-not-register-responses-for-every-request",
        ],
        consecutive=True,
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


def test_httpx_mock_already_matched_response(testdir: Testdir) -> None:
    """
    Already matched response should fail test case if
    can_send_already_matched_responses option is set to False (default).
    """
    testdir.makepyfile(
        """
        import httpx
        import pytest

        def test_httpx_mock_already_matched_response(httpx_mock):
            httpx_mock.add_response()
            with httpx.Client() as client:
                client.get("https://foo.tld")
                # Non mocked (already matched) request
                with pytest.raises(httpx.TimeoutException):
                    client.get("https://foo.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following requests were not expected:",
            "*  - GET request on https://foo.tld",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-not-register-responses-for-every-request",
        ],
        consecutive=True,
    )


def test_httpx_mock_reusing_matched_response(testdir: Testdir) -> None:
    """
    Already matched response should not fail test case if
    can_send_already_matched_responses option is set to True.
    """
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
        def test_httpx_mock_reusing_matched_response(httpx_mock):
            httpx_mock.add_response()
            with httpx.Client() as client:
                client.get("https://foo.tld")
                # Reusing response
                client.get("https://foo.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_httpx_mock_unmatched_request_without_responses(
    testdir: Testdir,
) -> None:
    testdir.makepyfile(
        """
        import httpx
        import pytest

        def test_httpx_mock_unmatched_request_without_responses(httpx_mock):
            with httpx.Client() as client:
                # This request will not be matched
                client.get("https://foo22.tld")
                # This code will not be reached
                client.get("https://foo3.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    # Assert the error that occurred
    result.stdout.fnmatch_lines(
        [
            "*httpx.TimeoutException: No response can be found for GET request on https://foo22.tld",
        ],
        consecutive=True,
    )
    # Assert the teardown assertion failure
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following requests were not expected:",
            "*  - GET request on https://foo22.tld",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-not-register-responses-for-every-request",
        ],
        consecutive=True,
    )


def test_httpx_mock_unmatched_request_with_only_unmatched_responses(
    testdir: Testdir,
) -> None:
    testdir.makepyfile(
        """
        import httpx
        import pytest

        def test_httpx_mock_unmatched_request_with_only_unmatched_responses(httpx_mock):
            # This response will not be sent (because of a typo in the URL)
            httpx_mock.add_response(url="https://foo2.tld")
            # This response will not be sent (because test execution failed earlier)
            httpx_mock.add_response(url="https://foo3.tld")
            
            with httpx.Client() as client:
                # This request will not be matched
                client.get("https://foo22.tld")
                # This code will not be reached
                client.get("https://foo3.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    # Assert the error that occurred
    result.stdout.fnmatch_lines(
        [
            "*httpx.TimeoutException: No response can be found for GET request on https://foo22.tld amongst:",
            "*- Match any request on https://foo2.tld",
            "*- Match any request on https://foo3.tld",
        ],
        consecutive=True,
    )
    # Assert the teardown assertion failure
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*  - Match any request on https://foo2.tld",
            "*  - Match any request on https://foo3.tld",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-register-more-responses-than-what-will-be-requested",
        ],
        consecutive=True,
    )


def test_httpx_mock_unmatched_request_with_only_unmatched_reusable_responses(
    testdir: Testdir,
) -> None:
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
        def test_httpx_mock_unmatched_request_with_only_unmatched_responses(httpx_mock):
            # This response will not be sent (because of a typo in the URL)
            httpx_mock.add_response(url="https://foo2.tld", method="GET")
            # This response will not be sent (because test execution failed earlier)
            httpx_mock.add_response(url="https://foo3.tld")
            
            with httpx.Client() as client:
                # This request will not be matched
                client.get("https://foo22.tld")
                # This code will not be reached
                client.get("https://foo3.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    # Assert the error that occurred
    result.stdout.fnmatch_lines(
        [
            "*httpx.TimeoutException: No response can be found for GET request on https://foo22.tld amongst:",
            "*- Match GET request on https://foo2.tld",
            "*- Match every request on https://foo3.tld",
        ],
        consecutive=True,
    )
    # Assert the teardown assertion failure
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*  - Match GET request on https://foo2.tld",
            "*  - Match every request on https://foo3.tld",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-register-more-responses-than-what-will-be-requested",
        ],
        consecutive=True,
    )


def test_httpx_mock_unmatched_request_with_only_matched_responses(
    testdir: Testdir,
) -> None:
    testdir.makepyfile(
        """
        import httpx
        import pytest

        def test_httpx_mock_unmatched_request_with_only_matched_responses(httpx_mock):
            # Sent response
            httpx_mock.add_response(url="https://foo.tld")
            # Sent response
            httpx_mock.add_response(url="https://foo.tld")
            
            with httpx.Client() as client:
                client.get("https://foo.tld")
                client.get("https://foo.tld")
                # This request will not be matched
                client.get("https://foo22.tld")
                # This code will not be reached
                client.get("https://foo3.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    # Assert the error that occurred
    result.stdout.fnmatch_lines(
        [
            "*httpx.TimeoutException: No response can be found for GET request on https://foo22.tld amongst:",
            "*- Already matched any request on https://foo.tld",
            "*- Already matched any request on https://foo.tld",
            "*",
            "*If you wanted to reuse an already matched response instead of registering it again, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-register-a-response-for-more-than-one-request",
        ],
        consecutive=True,
    )
    # Assert the teardown assertion failure
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following requests were not expected:",
            "*  - GET request on https://foo22.tld",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-not-register-responses-for-every-request",
        ],
        consecutive=True,
    )


def test_httpx_mock_unmatched_request_with_only_matched_reusable_responses(
    testdir: Testdir,
) -> None:
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
        def test_httpx_mock_unmatched_request_with_only_matched_responses(httpx_mock):
            # Sent response
            httpx_mock.add_response(url="https://foo.tld")
            # Sent response
            httpx_mock.add_response(url="https://foo3.tld")
            
            with httpx.Client() as client:
                client.get("https://foo.tld")
                client.get("https://foo.tld")
                client.get("https://foo3.tld")
                # This request will not be matched
                client.get("https://foo22.tld")
                # This code will not be reached
                client.get("https://foo3.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    # Assert the error that occurred
    result.stdout.fnmatch_lines(
        [
            "*httpx.TimeoutException: No response can be found for GET request on https://foo22.tld amongst:",
            "*- Match every request on https://foo.tld",
            "*- Match every request on https://foo3.tld",
        ],
        consecutive=True,
    )
    # Assert the teardown assertion failure
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following requests were not expected:",
            "*  - GET request on https://foo22.tld",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-not-register-responses-for-every-request",
        ],
        consecutive=True,
    )


def test_httpx_mock_unmatched_request_with_matched_and_unmatched_responses(
    testdir: Testdir,
) -> None:
    testdir.makepyfile(
        """
        import httpx
        import pytest

        def test_httpx_mock_unmatched_request_with_matched_and_unmatched_responses(httpx_mock):
            # Sent response
            httpx_mock.add_response(url="https://foo.tld")
            # This response will not be sent (because of a typo in the URL)
            httpx_mock.add_response(url="https://foo2.tld")
            # Sent response
            httpx_mock.add_response(url="https://foo.tld")
            # This response will not be sent (because test execution failed earlier)
            httpx_mock.add_response(url="https://foo3.tld")
            
            with httpx.Client() as client:
                client.get("https://foo.tld")
                client.get("https://foo.tld")
                # This request will not be matched
                client.get("https://foo22.tld")
                # This code will not be reached
                client.get("https://foo3.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    # Assert the error that occurred
    result.stdout.fnmatch_lines(
        [
            "*httpx.TimeoutException: No response can be found for GET request on https://foo22.tld amongst:",
            "*- Match any request on https://foo2.tld",
            "*- Match any request on https://foo3.tld",
            "*- Already matched any request on https://foo.tld",
            "*- Already matched any request on https://foo.tld",
            "*",
            "*If you wanted to reuse an already matched response instead of registering it again, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-register-a-response-for-more-than-one-request",
        ],
        consecutive=True,
    )
    # Assert the teardown assertion failure
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*  - Match any request on https://foo2.tld",
            "*  - Match any request on https://foo3.tld",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-register-more-responses-than-what-will-be-requested",
        ],
        consecutive=True,
    )


def test_httpx_mock_unmatched_request_with_matched_and_unmatched_reusable_responses(
    testdir: Testdir,
) -> None:
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.mark.httpx_mock(can_send_already_matched_responses=True)
        def test_httpx_mock_unmatched_request_with_matched_and_unmatched_responses(httpx_mock):
            # Sent response
            httpx_mock.add_response(url="https://foo.tld")
            # This response will not be sent (because of a typo in the URL)
            httpx_mock.add_response(url="https://foo33.tld")
            # Sent response
            httpx_mock.add_response(url="https://foo2.tld")
            # This response will not be sent (because test execution failed earlier)
            httpx_mock.add_response(url="https://foo4.tld")
            
            with httpx.Client() as client:
                client.get("https://foo.tld")
                client.get("https://foo2.tld")
                client.get("https://foo.tld")
                # This request will not be matched
                client.get("https://foo3.tld")
                # This code will not be reached
                client.get("https://foo2.tld")
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, failed=1)
    # Assert the error that occurred
    result.stdout.fnmatch_lines(
        [
            "*httpx.TimeoutException: No response can be found for GET request on https://foo3.tld amongst:",
            "*- Match every request on https://foo33.tld",
            "*- Match every request on https://foo4.tld",
            "*- Match every request on https://foo.tld",
            "*- Match every request on https://foo2.tld",
        ],
        consecutive=True,
    )
    # Assert the teardown assertion failure
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*  - Match every request on https://foo33.tld",
            "*  - Match every request on https://foo4.tld",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-register-more-responses-than-what-will-be-requested",
        ],
        consecutive=True,
    )


def test_httpx_mock_should_mock_sync(testdir: Testdir) -> None:
    """
    Non mocked requests should go through while other requests should be mocked.
    """
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.mark.httpx_mock(should_mock=lambda request: request.url.host != "localhost")
        def test_httpx_mock_should_mock_sync(httpx_mock):
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


def test_httpx_mock_should_mock_async(testdir: Testdir) -> None:
    """
    Non mocked requests should go through while other requests should be mocked.
    """
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.mark.asyncio
        @pytest.mark.httpx_mock(should_mock=lambda request: request.url.host != "localhost")
        async def test_httpx_mock_should_mock_async(httpx_mock):
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


def test_httpx_mock_options_on_multi_levels_are_aggregated(testdir: Testdir) -> None:
    """
    Test case ensures that every level provides one parameter that should be used in the end

    global (actually registered AFTER module): assert_all_responses_were_requested (tested by putting unused response)
    module: assert_all_requests_were_expected (tested by not mocking one URL)
    test: should_mock (tested by calling 3 URls, 2 mocked, the other one not)
    """
    testdir.makeconftest(
        """
        import pytest


        def pytest_collection_modifyitems(session, config, items):
            for item in items:
                item.add_marker(pytest.mark.httpx_mock(assert_all_responses_were_requested=False))
    """
    )
    testdir.makepyfile(
        """
        import httpx
        import pytest

        pytestmark = pytest.mark.httpx_mock(assert_all_requests_were_expected=False, should_mock=lambda request: request.url.host != "https://foo.tld")

        @pytest.mark.asyncio
        @pytest.mark.httpx_mock(should_mock=lambda request: request.url.host != "localhost")
        async def test_httpx_mock_options_on_multi_levels_are_aggregated(httpx_mock):
            httpx_mock.add_response(url="https://foo.tld", headers={"x-pytest-httpx": "this was mocked"})
            
            # This response will never be used, testing that assert_all_responses_were_requested is handled 
            httpx_mock.add_response(url="https://never_called.url")
            
            async with httpx.AsyncClient() as client:
                # Assert that previously set should_mock was overridden
                response = await client.get("https://foo.tld")
                assert response.headers["x-pytest-httpx"] == "this was mocked"
            
                # Assert that latest should_mock is handled
                with pytest.raises(httpx.ConnectError):
                    await client.get("https://localhost:5005")
            
                # Assert that assert_all_requests_were_expected is the one at module level
                with pytest.raises(httpx.TimeoutException):
                    await client.get("https://unexpected.url")
            
            # Assert that 2 requests out of 3 were mocked 
            assert len(httpx_mock.get_requests()) == 2
            
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
        def test_invalid_marker(httpx_mock):
            pass
            
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1)
    result.stdout.re_match_lines([r".*got an unexpected keyword argument 'foo'"])


def test_mandatory_response_not_matched(testdir: Testdir) -> None:
    """
    is_optional MUST take precedence over assert_all_responses_were_requested.
    """
    testdir.makepyfile(
        """
        import httpx
        import pytest

        @pytest.mark.httpx_mock(assert_all_responses_were_requested=False)
        def test_mandatory_response_not_matched(httpx_mock):
            # This response is optional and the fact that it was never requested should not trigger anything
            httpx_mock.add_response(url="https://test_url")
            # This response MUST be requested
            httpx_mock.add_response(url="https://test_url2", is_optional=False)
            
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    # Assert the teardown assertion failure
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*  - Match any request on https://test_url2",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-register-more-responses-than-what-will-be-requested",
        ],
        consecutive=True,
    )


def test_reusable_response_not_matched(testdir: Testdir) -> None:
    testdir.makepyfile(
        """
        import httpx

        def test_reusable_response_not_matched(httpx_mock):
            httpx_mock.add_response(url="https://test_url2", is_reusable=True)
            
    """
    )
    result = testdir.runpytest()
    result.assert_outcomes(errors=1, passed=1)
    # Assert the teardown assertion failure
    result.stdout.fnmatch_lines(
        [
            "*AssertionError: The following responses are mocked but not requested:",
            "*  - Match every request on https://test_url2",
            "*  ",
            "*  If this is on purpose, refer to https://github.com/Colin-b/pytest_httpx/blob/master/README.md#allow-to-register-more-responses-than-what-will-be-requested",
        ],
        consecutive=True,
    )
