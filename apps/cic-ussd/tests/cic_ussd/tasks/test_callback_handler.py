# standard imports
import json
from decimal import Decimal

# external imports
import celery
import pytest
import requests_mock
from chainlib.hash import strip_0x

# local imports
from cic_ussd.account.statement import generate, filter_statement_transactions
from cic_ussd.account.transaction import transaction_actors
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.db.models.account import Account
from cic_ussd.error import AccountCreationDataNotFound
from cic_ussd.metadata import PreferencesMetadata


# test imports
from tests.helpers.accounts import blockchain_address


def test_account_creation_callback(account_creation_data,
                                   cache_account_creation_data,
                                   celery_session_worker,
                                   custom_metadata,
                                   init_cache,
                                   init_database,
                                   load_chain_spec,
                                   mocker,
                                   setup_metadata_request_handler,
                                   setup_metadata_signer):
    phone_number = account_creation_data.get('phone_number')
    result = blockchain_address()
    task_uuid = account_creation_data.get('task_uuid')

    mock_task = mocker.patch('celery.app.task.Task.request')
    mock_task.root_id = task_uuid
    mock_task.delivery_info = {'routing_key': 'cic-ussd'}

    status_code = 1
    with pytest.raises(ValueError) as error:
        s_account_creation_callback = celery.signature(
            'cic_ussd.tasks.callback_handler.account_creation_callback', [task_uuid, '', status_code]
        )
        s_account_creation_callback.apply_async().get()
    assert str(error.value) == f'Unexpected status code: {status_code}'

    cached_account_creation_data = get_cached_data(task_uuid)
    cached_account_creation_data = json.loads(cached_account_creation_data)
    assert cached_account_creation_data.get('status') == account_creation_data.get('status')
    mock_add_phone_pointer = mocker.patch('cic_ussd.tasks.metadata.add_phone_pointer.apply_async')
    mock_add_custom_metadata = mocker.patch('cic_ussd.tasks.metadata.add_custom_metadata.apply_async')
    s_account_creation_callback = celery.signature(
        'cic_ussd.tasks.callback_handler.account_creation_callback', [result, '', 0]
    )
    s_account_creation_callback.apply_async().get()
    account = init_database.query(Account).filter_by(phone_number=phone_number).first()
    assert account.blockchain_address == result
    cached_account_creation_data = get_cached_data(task_uuid)
    cached_account_creation_data = json.loads(cached_account_creation_data)
    assert cached_account_creation_data.get('status') == 'CREATED'
    mock_add_phone_pointer.assert_called_with((result, phone_number), {}, queue='cic-ussd')
    mock_add_custom_metadata.assert_called_with((result, custom_metadata), {}, queue='cic-ussd')

    task_uuid = celery.uuid()
    mock_task.root_id = task_uuid
    with pytest.raises(AccountCreationDataNotFound) as error:
        s_account_creation_callback = celery.signature(
            'cic_ussd.tasks.callback_handler.account_creation_callback', [task_uuid, '', 0]
        )
        s_account_creation_callback.apply_async().get()
    assert str(error.value) == f'No account creation data found for task id: {task_uuid}'


def test_balances_callback(activated_account, balances, celery_session_worker):
    status_code = 1
    with pytest.raises(ValueError) as error:
        s_balances_callback = celery.signature(
            'cic_ussd.tasks.callback_handler.balances_callback',
            [balances, activated_account.blockchain_address, status_code])
        s_balances_callback.apply_async().get()
    assert str(error.value) == f'Unexpected status code: {status_code}.'

    status_code = 0
    s_balances_callback = celery.signature(
        'cic_ussd.tasks.callback_handler.balances_callback',
        [balances, activated_account.blockchain_address, status_code])
    s_balances_callback.apply_async().get()
    identifier = bytes.fromhex(strip_0x(activated_account.blockchain_address))
    key = cache_data_key(identifier, ':cic.balances')
    cached_balances = get_cached_data(key)
    cached_balances = json.loads(cached_balances)
    assert cached_balances == balances[0]


def test_statement_callback(activated_account, mocker, transactions_list):
    status_code = 1
    with pytest.raises(ValueError) as error:
        s_statement_callback = celery.signature(
            'cic_ussd.tasks.callback_handler.statement_callback',
            [transactions_list, activated_account.blockchain_address, status_code])
        s_statement_callback.apply_async().get()
    assert str(error.value) == f'Unexpected status code: {status_code}.'

    mock_task = mocker.patch('celery.app.task.Task.request')
    mock_task.delivery_info = {'routing_key': 'cic-ussd'}
    mock_statement_generate = mocker.patch('cic_ussd.tasks.processor.generate_statement.apply_async')
    status_code = 0
    s_statement_callback = celery.signature(
        'cic_ussd.tasks.callback_handler.statement_callback',
        [transactions_list, activated_account.blockchain_address, status_code])
    s_statement_callback.apply_async().get()
    statement_transactions = filter_statement_transactions(transactions_list)
    recipient_transaction, sender_transaction = transaction_actors(statement_transactions[0])
    sender_transaction['alt_blockchain_address'] = recipient_transaction.get('blockchain_address')
    mock_statement_generate.assert_called_with(
        (activated_account.blockchain_address, sender_transaction), {}, queue='cic-ussd')


def test_transaction_balances_callback(activated_account,
                                       balances,
                                       cache_balances,
                                       cache_default_token_data,
                                       cache_person_metadata,
                                       cache_preferences,
                                       load_chain_spec,
                                       mocker,
                                       preferences,
                                       setup_metadata_signer,
                                       setup_metadata_request_handler,
                                       set_locale_files,
                                       transaction_result):
    status_code = 1
    recipient_transaction, sender_transaction = transaction_actors(transaction_result)
    with pytest.raises(ValueError) as error:
        s_transaction_balances_callback = celery.signature(
            'cic_ussd.tasks.callback_handler.transaction_balances_callback',
            [balances, sender_transaction, status_code])
        s_transaction_balances_callback.apply_async().get()
    assert str(error.value) == f'Unexpected status code: {status_code}.'
    mocked_chain = mocker.patch('celery.chain')
    mock_task_request = mocker.patch('celery.app.task.Task.request')
    mock_task_request.delivery_info = {'routing_key': 'cic-ussd'}
    sender_transaction['transaction_type'] = 'transfer'
    status_code = 0
    s_transaction_balances_callback = celery.signature(
        'cic_ussd.tasks.callback_handler.transaction_balances_callback',
        [balances, sender_transaction, status_code])
    s_transaction_balances_callback.apply_async().get()
    mocked_chain.assert_called()
    sender_transaction['transaction_type'] = 'tokengift'
    status_code = 0
    s_transaction_balances_callback = celery.signature(
        'cic_ussd.tasks.callback_handler.transaction_balances_callback',
        [balances, sender_transaction, status_code])
    s_transaction_balances_callback.apply_async().get()
    mocked_chain.assert_called()


def test_transaction_callback(load_chain_spec, mock_async_balance_api_query, transaction_result):
    status_code = 1
    with pytest.raises(ValueError) as error:
        s_transaction_callback = celery.signature(
            'cic_ussd.tasks.callback_handler.transaction_callback',
            [transaction_result, 'transfer', status_code])
        s_transaction_callback.apply_async().get()
    assert str(error.value) == f'Unexpected status code: {status_code}.'

    status_code = 0
    s_transaction_callback = celery.signature(
        'cic_ussd.tasks.callback_handler.transaction_callback',
        [transaction_result, 'transfer', status_code])
    s_transaction_callback.apply_async().get()
    recipient_transaction, sender_transaction = transaction_actors(transaction_result)
    assert mock_async_balance_api_query.get('address') == recipient_transaction.get('blockchain_address') or sender_transaction.get('blockchain_address')
    assert mock_async_balance_api_query.get('token_symbol') == recipient_transaction.get('token_symbol') or sender_transaction.get('token_symbol')


