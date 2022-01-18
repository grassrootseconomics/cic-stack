import pytest
from cic_eth.server.converters import from_wei, to_wei, truncate


@pytest.mark.parametrize("expected, decimals, value", [
    (1, 6, 1_000_000),
    (500, 9, 500_000_000_000)
])
def test_from_wei(value, decimals, expected):
    assert expected == from_wei(value=value, decimals=decimals)


@pytest.mark.parametrize("expected, decimals, value", [
    (10_000_000_000, 10, 1),
    (500_000_000, 6, 500)
])
def test_to_wei(value, decimals, expected):
    assert expected == to_wei(value=value, decimals=decimals)


@pytest.mark.parametrize("expected, decimals, value", [
    (1.234567, 6, 1.23456789),
    (0.1003209999, 10, 0.100321),
    (1.0, 0, 1),
    (0.0, 2, 0.000413)

])
def test_truncate(expected, decimals, value):
    assert expected == truncate(value=value, decimals=decimals)
