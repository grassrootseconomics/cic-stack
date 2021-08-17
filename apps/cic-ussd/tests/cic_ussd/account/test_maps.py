# standard imports

# external imports
import pytest

# local imports
from cic_ussd.account.maps import gender, language

# test imports


@pytest.mark.parametrize('key, expected_value', [
    ('1', 'male'),
    ('2', 'female'),
    ('3', 'other')
])
def test_gender(key, expected_value):
    g_map = gender()
    assert g_map[key] == expected_value


@pytest.mark.parametrize('key, expected_value', [
    ('1', 'en'),
    ('2', 'sw'),
])
def test_language(key, expected_value):
    l_map = language()
    assert l_map[key] == expected_value
