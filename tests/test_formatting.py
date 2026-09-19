import pytest

from unisimu.formatting import format_scientific


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, "0"),
        (0.05, "0.05"),
        (12.345, "12.35"),
        (713.2, "713.2"),
        (4165, "4,165"),
        (68430, "68,430"),
        (0.00012, "1.2×10⁻⁴"),
        (2.9e8, "2.9×10⁸"),
        (1e6, "1.0×10⁶"),
    ],
)
def test_format_scientific(value, expected):
    assert format_scientific(value) == expected
