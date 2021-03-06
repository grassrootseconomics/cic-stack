# standard imports
import json

# third-party imports
import pytest

# local imports
from cic_ussd.state_machine.logic.transaction import (has_sufficient_balance,
                                                      is_valid_recipient,
                                                      is_valid_transaction_amount,
                                                      process_transaction_request,
                                                      save_recipient_phone_to_session_data,
                                                      save_transaction_amount_to_session_data)
from cic_ussd.redis import InMemoryStore


@pytest.mark.parametrize("amount, expected_result", [
    ('50', True),
    ('', False)
])
def test_is_valid_transaction_amount(create_activated_user, create_in_db_ussd_session, amount, expected_result):
    state_machine_data = (amount, create_in_db_ussd_session, create_activated_user)
    validity = is_valid_transaction_amount(state_machine_data=state_machine_data)
    assert validity == expected_result


def test_save_recipient_phone_to_session_data(create_activated_user,
                                              create_in_db_ussd_session,
                                              celery_session_worker,
                                              create_in_redis_ussd_session,
                                              init_database):
    phone_number = '+254712345678'
    in_memory_ussd_session = InMemoryStore.cache.get('AT974186')
    in_memory_ussd_session = json.loads(in_memory_ussd_session)

    assert in_memory_ussd_session.get('session_data') == {}
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (phone_number, serialized_in_db_ussd_session, create_activated_user)
    save_recipient_phone_to_session_data(state_machine_data=state_machine_data)

    in_memory_ussd_session = InMemoryStore.cache.get('AT974186')
    in_memory_ussd_session = json.loads(in_memory_ussd_session)

    assert in_memory_ussd_session.get('session_data')['recipient_phone_number'] == phone_number


def test_save_transaction_amount_to_session_data(create_activated_user,
                                                 create_in_db_ussd_session,
                                                 celery_session_worker,
                                                 create_in_redis_ussd_session,
                                                 init_database):
    transaction_amount = '100'
    in_memory_ussd_session = InMemoryStore.cache.get('AT974186')
    in_memory_ussd_session = json.loads(in_memory_ussd_session)

    assert in_memory_ussd_session.get('session_data') == {}
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (transaction_amount, serialized_in_db_ussd_session, create_activated_user)
    save_transaction_amount_to_session_data(state_machine_data=state_machine_data)

    in_memory_ussd_session = InMemoryStore.cache.get('AT974186')
    in_memory_ussd_session = json.loads(in_memory_ussd_session)

    assert in_memory_ussd_session.get('session_data')['transaction_amount'] == transaction_amount


@pytest.mark.parametrize("test_value, expected_result", [
    ('45', True),
    ('75', False)
])
def test_has_sufficient_balance(mock_balance,
                                create_in_db_ussd_session,
                                create_valid_tx_sender,
                                expected_result,
                                test_value):
    mock_balance(60)
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (test_value, serialized_in_db_ussd_session, create_valid_tx_sender)
    result = has_sufficient_balance(state_machine_data=state_machine_data)
    assert result == expected_result


@pytest.mark.parametrize("test_value, expected_result", [
    ('+25498765432', True),
    ('+25498765433', False)
])
def test_is_valid_recipient(create_in_db_ussd_session,
                            create_valid_tx_recipient,
                            create_valid_tx_sender,
                            expected_result,
                            test_value):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = (test_value, serialized_in_db_ussd_session, create_valid_tx_sender)
    result = is_valid_recipient(state_machine_data=state_machine_data)
    assert result == expected_result


def test_process_transaction_request(create_valid_tx_recipient,
                                     create_valid_tx_sender,
                                     load_config,
                                     mock_outgoing_transactions,
                                     setup_chain_spec,
                                     ussd_session_data):
    ussd_session_data['session_data'] = {
        'recipient_phone_number': create_valid_tx_recipient.phone_number,
        'transaction_amount': '50'
    }
    state_machine_data = ('', ussd_session_data, create_valid_tx_sender)
    process_transaction_request(state_machine_data=state_machine_data)
    assert mock_outgoing_transactions[0].get('amount') == 50.0
    assert mock_outgoing_transactions[0].get('token_symbol') == 'SRF'
