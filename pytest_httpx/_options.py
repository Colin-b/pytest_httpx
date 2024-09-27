from typing import Optional


class _HTTPXMockOptions:
    def __init__(
        self,
        *,
        assert_all_responses_were_requested: bool = True,
        assert_all_requests_were_expected: bool = True,
        can_send_already_matched_responses: bool = False,
        non_mocked_hosts: Optional[list[str]] = None,
    ) -> None:
        self.assert_all_responses_were_requested = assert_all_responses_were_requested
        self.assert_all_requests_were_expected = assert_all_requests_were_expected
        self.can_send_already_matched_responses = can_send_already_matched_responses

        if non_mocked_hosts is None:
            non_mocked_hosts = []

        # Ensure redirections to www hosts are handled transparently.
        missing_www = [
            f"www.{host}" for host in non_mocked_hosts if not host.startswith("www.")
        ]
        self.non_mocked_hosts = [*non_mocked_hosts, *missing_www]
