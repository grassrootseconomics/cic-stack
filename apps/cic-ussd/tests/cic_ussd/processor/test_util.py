# standard imports
import datetime
import json

# external imports
import pytest
from chainlib.hash import strip_0x
from cic_types.models.person import get_contact_data_from_vcard

# local imports
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.metadata import PersonMetadata
from cic_ussd.processor.util import (latest_input,
                                     parse_person_metadata,
                                     resume_last_ussd_session,
                                     ussd_menu_list)
from cic_ussd.translation import translation_for


# test imports


@pytest.mark.parametrize('user_input, expected_value', [
    ('1*9*6*7', '7'),
    ('1', '1'),
    ('', '')
])
def test_latest_input(user_input, expected_value):
    assert latest_input(user_input) == expected_value


def test_parse_person_metadata(activated_account, cache_person_metadata, cache_preferences):
    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    person_metadata = PersonMetadata(identifier)
    cached_person_metadata = person_metadata.get_cached_metadata()
    person_metadata = json.loads(cached_person_metadata)
    preferred_language = get_cached_preferred_language(activated_account.blockchain_address)
    display_key = 'ussd.display_person_metadata'
    parsed_person_metadata = parse_person_metadata(cached_person_metadata,
                                                   display_key,
                                                   preferred_language)
    contact_data = get_contact_data_from_vcard(person_metadata.get('vcard'))
    full_name = f'{contact_data.get("given")} {contact_data.get("family")}'
    date_of_birth = person_metadata.get('date_of_birth')
    year_of_birth = date_of_birth.get('year')
    present_year = datetime.datetime.now().year
    age = present_year - year_of_birth
    gender = person_metadata.get('gender')
    products = ', '.join(person_metadata.get('products'))
    location = person_metadata.get('location').get('area_name')
    assert parsed_person_metadata == translation_for(key=display_key,
                                                     preferred_language=preferred_language,
                                                     full_name=full_name,
                                                     age=age,
                                                     gender=gender,
                                                     location=location,
                                                     products=products)


@pytest.mark.parametrize('last_state, expected_menu_name', [
    ('account_creation_prompt', 'start'),
    ('enter_transaction_recipient', 'enter_transaction_recipient')
])
def test_resume_last_ussd_session(expected_menu_name, last_state, load_ussd_menu):
    assert resume_last_ussd_session(last_state).get('name') == expected_menu_name


def test_ussd_menu_list(activated_account, cache_preferences, load_ussd_menu, set_locale_files):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    fallback = translation_for('helpers.no_transaction_history', preferred_language)
    menu_list_sets = ['1. FII 50.0', '2. GFT 60.0', '3. DET 49.99']
    split = 3
    menu_list = ussd_menu_list(fallback=fallback, menu_list=menu_list_sets, split=split)
    menu_list_sets = [menu_list_sets[item:item + split] for item in range(0, len(menu_list), split)]
    menu_list_reprs = []
    for i in range(split):
        try:
            menu_list_reprs.append(''.join(f'{list_set_item}\n' for list_set_item in menu_list_sets[i]).rstrip('\n'))
        except IndexError:
            menu_list_reprs.append(fallback)
    assert menu_list == menu_list_reprs
