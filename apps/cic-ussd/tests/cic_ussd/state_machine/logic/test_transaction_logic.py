# standard imports
import json

# external imports
import pytest
import requests_mock
from chainlib.hash import strip_0x

# local imports
from cic_ussd.account.transaction import to_wei
from cic_ussd.cache import get_cached_data
from cic_ussd.metadata import PersonMetadata
from cic_ussd.state_machine.logic.transaction import (is_valid_recipient,
                                                      is_valid_transaction_amount,
                                                      has_sufficient_balance,
                                                      process_transaction_request,
                                                      retrieve_recipient_metadata,
                                                      save_recipient_phone_to_session_data,
                                                      save_transaction_amount_to_session_data)


# test imports


def test_is_valid_recipient(activated_account,
                            generic_ussd_session,
                            init_database,
                            load_e164_region,
                            pending_account,
                            valid_recipient):
    state_machine = ('0112365478', generic_ussd_session, valid_recipient, init_database)
    assert is_valid_recipient(state_machine) is False
    state_machine = (valid_recipient.phone_number, generic_ussd_session, activated_account, init_database)
    assert is_valid_recipient(state_machine) is True


@pytest.mark.parametrize("amount, expected_result", [
    ('50', True),
    ('', False)
])
def test_is_valid_transaction_amount(activated_account, amount, expected_result, generic_ussd_session, init_database):
    state_machine_data = (amount, generic_ussd_session, activated_account, init_database)
    assert is_valid_transaction_amount(state_machine_data) is expected_result


@pytest.mark.parametrize("value, expected_result", [
    ('45', True),
    ('75', False)
])
def test_has_sufficient_balance(activated_account,
                                cache_balances,
                                cache_default_token_data,
                                expected_result,
                                generic_ussd_session,
                                init_database,
                                value):
    state_machine_data = (value, generic_ussd_session, activated_account, init_database)
    assert has_sufficient_balance(state_machine_data=state_machine_data) == expected_result


def test_process_transaction_request(activated_account,
                                     cache_default_token_data,
                                     cached_ussd_session,
                                     celery_session_worker,
                                     init_cache,
                                     init_database,
                                     load_chain_spec,
                                     load_config,
                                     mock_transfer_api,
                                     valid_recipient):
    cached_ussd_session.set_data('recipient_phone_number', valid_recipient.phone_number)
    cached_ussd_session.set_data('transaction_amount', '50')
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    state_machine_data = ('', ussd_session, activated_account, init_database)
    process_transaction_request(state_machine_data)
    assert mock_transfer_api['from_address'] == activated_account.blockchain_address
    assert mock_transfer_api['to_address'] == valid_recipient.blockchain_address
    assert mock_transfer_api['value'] == to_wei(50)
    assert mock_transfer_api['token_symbol'] == load_config.get('TEST_TOKEN_SYMBOL')


def test_retrieve_recipient_metadata(activated_account,
                                     generic_ussd_session,
                                     init_database,
                                     load_chain_spec,
                                     mocker,
                                     valid_recipient):
    state_machine_data = (valid_recipient.phone_number, generic_ussd_session, activated_account, init_database)
    mocked_query_metadata = mocker.patch('cic_ussd.tasks.metadata.query_person_metadata.apply_async')
    retrieve_recipient_metadata(state_machine_data)
    mocked_query_metadata.assert_called_with((valid_recipient.blockchain_address, ), {}, queue='cic-ussd')


def test_transaction_information_to_session_data(activated_account,
                                                 cached_ussd_session,
                                                 init_cache,
                                                 init_database,
                                                 load_e164_region,
                                                 valid_recipient):
    assert cached_ussd_session.to_json()['data'] == {}
    state_machine_data = (valid_recipient.phone_number, cached_ussd_session.to_json(), activated_account, init_database)
    save_recipient_phone_to_session_data(state_machine_data)
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    assert ussd_session.get('data')['recipient_phone_number'] == valid_recipient.phone_number
    state_machine_data = ('25', cached_ussd_session.to_json(), activated_account, init_database)
    save_transaction_amount_to_session_data(state_machine_data)
    ussd_session = get_cached_data(cached_ussd_session.external_session_id)
    ussd_session = json.loads(ussd_session)
    assert ussd_session.get('data')['transaction_amount'] == '25'
