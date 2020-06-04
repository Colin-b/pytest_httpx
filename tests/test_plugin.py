def test_fixture_is_available(testdir):
    # create a temporary pytest test file
    testdir.makepyfile("""
        import httpx
        
        
        def test_http(httpx_mock):
            mock = httpx_mock.add_response(url="http://foo.tld")
            r = httpx.get("http://foo.tld")
            assert httpx_mock.get_request() is not None

    """)

    # run all tests with pytest
    result = testdir.runpytest()
    result.assert_outcomes(passed=1)


def test_httpx_mock_unused_response(testdir):
    """
    Unused responses should fail test case.
    """
    testdir.makepyfile("""
        def test_httpx_mock_unused_response(httpx_mock):
            httpx_mock.add_response()
    """)
    result = testdir.runpytest()
    result.assert_outcomes(error=1, passed=1)
    result.stdout.fnmatch_lines([
        '*AssertionError: The following responses are mocked but not requested: *'
    ])


def test_httpx_mock_unused_callback(testdir):
    """
    Unused callbacks should fail test case.
    """
    testdir.makepyfile("""
        def test_httpx_mock_unused_callback(httpx_mock):
            def unused(*args, **kwargs):
                pass
        
            httpx_mock.add_callback(unused)

    """)
    result = testdir.runpytest()
    result.assert_outcomes(error=1, passed=1)
    result.stdout.fnmatch_lines([
        '*AssertionError: The following callbacks are registered but not executed: *'
    ])
