# standard imports
import os

# external imports
import pytest

# local imports
from cic_ussd.translation import translation_for

# test imports
from tests.helpers.accounts import blockchain_address


@pytest.fixture(scope='function')
def mock_account_creation_task_request(mocker, task_uuid):
    def mock_request(self):
        mocked_task_request = mocker.patch('celery.app.task.Task.request')
        mocked_task_request.id = task_uuid
        return mocked_task_request
    mocker.patch('cic_eth.api.api_task.Api.create_account', mock_request)


@pytest.fixture(scope='function')
def mock_account_creation_task_result(mocker, task_uuid):
    def task_result(self):
        sync_res = mocker.patch('celery.result.AsyncResult')
        sync_res.id = task_uuid
        sync_res.get.return_value = blockchain_address()
        return sync_res
    mocker.patch('cic_eth.api.api_task.Api.create_account', task_result)


@pytest.fixture(scope='function')
def mock_async_balance_api_query(mocker):
    query_args = {}

    def async_api_query(self, address: str, token_symbol: str):
        query_args['address'] = address
        query_args['token_symbol'] = token_symbol
    mocker.patch('cic_eth.api.api_task.Api.balance', async_api_query)
    return query_args


@pytest.fixture(scope='function')
def mock_get_adjusted_balance(mocker, task_uuid):
    query_args = {}

    def get_adjusted_balance(self, token_symbol, balance, timestamp):
        sync_res = mocker.patch('celery.result.AsyncResult')
        sync_res.id = task_uuid
        sync_res.result = 45931650.64654012
        query_args['balance'] = balance
        query_args['timestamp'] = timestamp
        query_args['token_symbol'] = token_symbol
        return sync_res
    mocker.patch('cic_eth_aux.erc20_demurrage_token.api.Api.get_adjusted_balance', get_adjusted_balance)
    return query_args


@pytest.fixture(scope='function')
def mock_notifier_api(mocker):
    sms = {}

    def mock_sms_api(self, message: str, recipient: str):
        pass

    def send_sms_notification(self, key: str, phone_number: str, preferred_language: str, **kwargs):
        message = translation_for(key=key, preferred_language=preferred_language, **kwargs)
        sms['message'] = message
        sms['recipient'] = phone_number

    mocker.patch('cic_notify.api.Api.sms', mock_sms_api)
    mocker.patch('cic_ussd.notifications.Notifier.send_sms_notification', send_sms_notification)
    return sms


@pytest.fixture(scope='function')
def mock_sync_balance_api_query(balances, mocker, task_uuid):
    def sync_api_query(self, address: str, token_symbol: str):
        sync_res = mocker.patch('celery.result.AsyncResult')
        sync_res.id = task_uuid
        sync_res.get.return_value = balances
        return sync_res
    mocker.patch('cic_eth.api.api_task.Api.balance', sync_api_query)


@pytest.fixture(scope='function')
def mock_sync_default_token_api_query(default_token_data, mocker, task_uuid):
    def mock_query(self):
        sync_res = mocker.patch('celery.result.AsyncResult')
        sync_res.id = task_uuid
        sync_res.get.return_value = default_token_data
        return sync_res
    mocker.patch('cic_eth.api.api_task.Api.default_token', mock_query)


@pytest.fixture(scope='function')
def mock_transaction_list_query(mocker):
    query_args = {}

    def mock_query(self, address: str, limit: int):
        query_args['address'] = address
        query_args['limit'] = limit

    mocker.patch('cic_eth.api.api_task.Api.list', mock_query)
    return query_args


@pytest.fixture(scope='function')
def mock_transfer_api(mocker):
    transfer_args = {}

    def mock_transfer(self, from_address: str, to_address: str, value: int, token_symbol: str):
        transfer_args['from_address'] = from_address
        transfer_args['to_address'] = to_address
        transfer_args['value'] = value
        transfer_args['token_symbol'] = token_symbol

    mocker.patch('cic_eth.api.api_task.Api.transfer', mock_transfer)
    return transfer_args
