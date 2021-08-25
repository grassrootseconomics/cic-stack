# standard imports
import json

# external imports
from cic_types.models.person import get_contact_data_from_vcard

# local imports
from cic_ussd.account.metadata import get_cached_preferred_language, parse_account_metadata

# test imports
from tests.helpers.accounts import blockchain_address


def test_get_cached_preferred_language(activated_account, cache_preferences, preferences):
    cached_preferred_language = get_cached_preferred_language(activated_account.blockchain_address)
    assert cached_preferred_language == preferences.get('preferred_language')
    cached_preferred_language = get_cached_preferred_language(blockchain_address())
    assert cached_preferred_language is None


def test_parse_account_metadata(person_metadata):
    contact_information = get_contact_data_from_vcard(person_metadata.get('vcard'))
    given_name = contact_information.get('given')
    family_name = contact_information.get('family')
    phone_number = contact_information.get('tel')
    parsed_account_metadata = f'{given_name} {family_name} {phone_number}'
    assert parse_account_metadata(person_metadata) == parsed_account_metadata

