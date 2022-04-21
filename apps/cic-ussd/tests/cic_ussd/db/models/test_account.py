# standard imports
import json

# external imports
import pytest
from cic_types.models.person import get_contact_data_from_vcard

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.cache import get_cached_data
from cic_ussd.db.enum import AccountStatus
from cic_ussd.db.models.account import Account, create, cache_creation_task_uuid
from cic_ussd.db.models.task_tracker import TaskTracker

# test imports
from tests.helpers.accounts import blockchain_address, phone_number


def test_account(init_database):
    address = blockchain_address()
    phone = phone_number()
    account = Account(address, phone)
    account.create_password('0000')
    account.activate_account()
    init_database.add(account)
    init_database.commit()

    account = init_database.query(Account).get(1)
    assert account.blockchain_address == address
    assert account.phone_number == phone
    assert account.failed_pin_attempts == 0
    assert account.verify_password('0000') is True
    assert account.get_status(init_database) == AccountStatus.ACTIVE.name


def test_account_repr(activated_account):
    assert repr(activated_account) == f'<Account: {activated_account.blockchain_address}>'


def test_account_statuses(init_database, pending_account):
    assert pending_account.get_status(init_database) == AccountStatus.PENDING.name
    pending_account.create_password('1111')
    pending_account.activate_account()
    init_database.add(pending_account)
    init_database.commit()
    assert pending_account.get_status(init_database) == AccountStatus.ACTIVE.name
    pending_account.failed_pin_attempts = 3
    assert pending_account.get_status(init_database) == AccountStatus.LOCKED.name
    pending_account.reset_pin(init_database)
    assert pending_account.get_status(init_database) == AccountStatus.RESET.name
    pending_account.activate_account()
    assert pending_account.get_status(init_database) == AccountStatus.ACTIVE.name


def test_get_by_phone_number(activated_account, init_database):
    account = Account.get_by_phone_number(activated_account.phone_number, init_database)
    assert account == activated_account


def test_has_preferred_language(activated_account, cache_preferences):
    assert activated_account.has_preferred_language() is True


def test_lacks_preferred_language(activated_account):
    assert activated_account.has_preferred_language() is False


def test_has_valid_pin(activated_account, init_database, pending_account):
    assert activated_account.has_valid_pin(init_database) is True
    assert pending_account.has_valid_pin(init_database) is False


def test_pin_is_blocked(activated_account, init_database):
    assert activated_account.pin_is_blocked(init_database) is False
    activated_account.failed_pin_attempts = 3
    init_database.add(activated_account)
    init_database.commit()
    assert activated_account.pin_is_blocked(init_database) is True


def test_standard_metadata_id(activated_account, cache_person_metadata, pending_account, person_metadata):
    contact_information = get_contact_data_from_vcard(person_metadata.get('vcard'))
    given_name = contact_information.get('given')
    family_name = contact_information.get('family')
    phone_number = contact_information.get('tel')
    parsed_account_metadata = f'{given_name} {family_name} {phone_number}'
    assert activated_account.standard_metadata_id() == parsed_account_metadata
    assert pending_account.standard_metadata_id() == pending_account.phone_number


def test_account_create(init_cache, init_database, load_chain_spec, mock_account_creation_task_result, task_uuid):
    chain_str = Chain.spec.__str__()
    create(chain_str, phone_number(), init_database, 'en')
    assert len(init_database.query(TaskTracker).all()) == 1
    account_creation_data = get_cached_data(task_uuid)
    assert json.loads(account_creation_data).get('status') == AccountStatus.PENDING.name


def test_reset_pin(init_database, activated_account):
    assert activated_account.get_status(init_database) == AccountStatus.ACTIVE.name
    activated_account.failed_pin_attempts = 1
    activated_account.reset_pin(init_database, True)
    assert activated_account.get_status(init_database) == AccountStatus.ACTIVE.name
    activated_account.reset_pin(init_database)
    assert activated_account.get_status(init_database) == AccountStatus.RESET.name
