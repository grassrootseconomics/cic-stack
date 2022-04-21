# standard imports

# external imports
import pytest

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.account.transaction import (aux_transaction_data,
                                          from_wei,
                                          to_wei,
                                          truncate,
                                          transaction_actors,
                                          validate_transaction_account,
                                          OutgoingTransaction)
from cic_ussd.db.models.account import Account
from cic_ussd.error import UnknownUssdRecipient
from cic_ussd.translation import translation_for


# test imports


def check_aux_data(action_tag_key, direction_tag_key, preferred_language, transaction_with_aux_data):
    assert transaction_with_aux_data.get('action_tag') == translation_for(action_tag_key, preferred_language)
    assert transaction_with_aux_data.get('direction_tag') == translation_for(direction_tag_key, preferred_language)


def test_aux_transaction_data(preferences, set_locale_files, transactions_list):
    sample_transaction = transactions_list[0]
    preferred_language = preferences.get('preferred_language')
    recipient_transaction, sender_transaction = transaction_actors(sample_transaction)
    recipient_tx_aux_data = aux_transaction_data(preferred_language, recipient_transaction)
    check_aux_data('helpers.received', 'helpers.from', preferred_language, recipient_tx_aux_data)
    sender_tx_aux_data = aux_transaction_data(preferred_language, sender_transaction)
    check_aux_data('helpers.sent', 'helpers.to', preferred_language, sender_tx_aux_data)


@pytest.mark.parametrize("value, expected_result", [
    (50000000, 50.0),
    (100000, 0.1)
])
def test_from_wei(cache_default_token_data, expected_result, value):
    assert from_wei(6, value) == expected_result


@pytest.mark.parametrize("value, expected_result", [
    (50, 50000000),
    (0.10, 100000)
])
def test_to_wei(cache_default_token_data, expected_result, value):
    assert to_wei(6, value) == expected_result


@pytest.mark.parametrize("decimals, value, expected_result", [
    (3, 1234.32875, 1234.328),
    (2, 98.998, 98.99)
])
def test_truncate(decimals, value, expected_result):
    assert truncate(value=value, decimals=decimals).__float__() == expected_result


def test_transaction_actors(activated_account, transaction_result, valid_recipient):
    recipient_transaction, sender_transaction = transaction_actors(transaction_result)
    assert recipient_transaction.get('blockchain_address') == valid_recipient.blockchain_address
    assert sender_transaction.get('blockchain_address') == activated_account.blockchain_address
    assert recipient_transaction.get('role') == 'recipient'
    assert sender_transaction.get('role') == 'sender'
    assert recipient_transaction.get('token_symbol') == transaction_result.get('destination_token_symbol')
    assert sender_transaction.get('token_symbol') == transaction_result.get('source_token_symbol')
    assert recipient_transaction.get('token_value') == transaction_result.get('destination_token_value')
    assert sender_transaction.get('token_value') == transaction_result.get('source_token_value')


def test_validate_transaction_account(activated_account, init_database, transactions_list):
    sample_transaction = transactions_list[0]
    recipient_transaction, sender_transaction = transaction_actors(sample_transaction)
    recipient_account = validate_transaction_account(
        recipient_transaction.get('blockchain_address'), recipient_transaction.get('role'), init_database)
    sender_account = validate_transaction_account(
        sender_transaction.get('blockchain_address'), sender_transaction.get('role'),  init_database)
    assert isinstance(recipient_account, Account)
    assert isinstance(sender_account, Account)
    sample_transaction = transactions_list[1]
    recipient_transaction, sender_transaction = transaction_actors(sample_transaction)
    with pytest.raises(UnknownUssdRecipient) as error:
        validate_transaction_account(
            recipient_transaction.get('blockchain_address'), recipient_transaction.get('role'), init_database)
    assert str(
        error.value) == f'Tx for recipient: {recipient_transaction.get("blockchain_address")} has no matching account in the system.'
    validate_transaction_account(
        sender_transaction.get('blockchain_address'), sender_transaction.get('role'), init_database)
    assert f'Tx from sender: {sender_transaction.get("blockchain_address")} has no matching account in system.'


@pytest.mark.parametrize("amount", [50, 0.10])
def test_outgoing_transaction_processor(activated_account,
                                        amount,
                                        cache_default_token_data,
                                        celery_session_worker,
                                        load_config,
                                        load_chain_spec,
                                        mock_transfer_api,
                                        valid_recipient):
    chain_str = Chain.spec.__str__()
    token_symbol = load_config.get('TEST_TOKEN_SYMBOL')
    outgoing_tx_processor = OutgoingTransaction(chain_str,
                                                activated_account.blockchain_address,
                                                valid_recipient.blockchain_address)

    outgoing_tx_processor.transfer(amount, 6, token_symbol)
    assert mock_transfer_api.get('from_address') == activated_account.blockchain_address
    assert mock_transfer_api.get('to_address') == valid_recipient.blockchain_address
    assert mock_transfer_api.get('value') == to_wei(6, amount)
    assert mock_transfer_api.get('token_symbol') == token_symbol
