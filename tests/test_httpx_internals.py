import pytest

from pytest_httpx._httpx_internals import PrimitiveData, _primitive_value_to_str


@pytest.mark.parametrize(
    ("incoming_value", "expected_result"),
    [
        (True, "true"),
        (False, "false"),
        (1, "1"),
        (1.0, "1.0"),
        ("string", "string"),
    ],
)
def test_primitive_value_to_str(
    incoming_value: PrimitiveData, expected_result: str
) -> None:
    assert _primitive_value_to_str(incoming_value) == expected_result
