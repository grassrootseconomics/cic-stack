# standard imports
import pytest

from cic_ussd.state_machine.logic.util import cash_rounding_precision

@pytest.mark.parametrize("test_input,expected", [("2", 2.0), ("2.5", 2.5), ("2.55", 2.55), ("2.559", 2.55), ("2.551", 2.55), ("2.99999999", 2.99)])
def test_precision(test_input, expected):
    assert cash_rounding_precision(test_input) == expected

def test_high_precision():
    with pytest.raises(AssertionError):
        cash_rounding_precision("3.9999999999999999999999999")
