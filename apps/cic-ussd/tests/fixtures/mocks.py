# standard imports
import json
from io import StringIO

# third-party imports
import pytest

# local imports
from cic_ussd.translation import translation_for
from cic_ussd.transactions import truncate


@pytest.fixture(scope='function')
def mock_meta_post_response():
    return {
        'name': 'cic',
        'version': '1',
        'ext': {
            'network': {
                'name': 'pgp',
                'version': '2'
            },
            'engine': {
                'name': 'automerge',
                'version': '0.14.1'
            }
        },
        'payload': '["~#iL",[["~#iM",["ops",["^0",[["^1",["action","set","obj","00000000-0000-0000-0000-000000000000",'
                   '"key","id","value","7e2f58335a69ac82f9a965a8fc35403c8585ea601946d858ee97684a285bf857"]],["^1",'
                   '["action","set","obj","00000000-0000-0000-0000-000000000000","key","timestamp","value",'
                   '1613487781]], '
                   '["^1",["action","set","obj","00000000-0000-0000-0000-000000000000","key","data","value",'
                   '"{\\"foo\\": '
                   '\\"bar\\", \\"xyzzy\\": 42}"]]]],"actor","2b738a75-2aad-4ac8-ae8d-294a5ea4afad","seq",1,"deps",'
                   '["^1", '
                   '[]],"message","Initialization","undoable",false]],["^1",["ops",["^0",[["^1",["action","makeMap",'
                   '"obj","a921a5ae-0554-497a-ac2e-4e829d8a12b6"]],["^1",["action","set","obj",'
                   '"a921a5ae-0554-497a-ac2e-4e829d8a12b6","key","digest","value","W10="]],["^1",["action","link",'
                   '"obj", '
                   '"00000000-0000-0000-0000-000000000000","key","signature","value",'
                   '"a921a5ae-0554-497a-ac2e-4e829d8a12b6"]]]],"actor","2b738a75-2aad-4ac8-ae8d-294a5ea4afad","seq",2,'
                   '"deps",["^1",[]],"message","sign"]]]]',
        'digest': 'W10='
    }


@pytest.fixture(scope='function')
def mock_meta_get_response():
    return {
        "foo": "bar",
        "xyzzy": 42
    }


@pytest.fixture(scope='function')
def mock_notifier_api(mocker):
    messages = []

    def mock_sms_api(self, message: str, recipient: str):
        pass

    def mock_send_sms_notification(self, key: str, phone_number: str, preferred_language: str, **kwargs):
        message = translation_for(key=key, preferred_language=preferred_language, **kwargs)
        messages.append({'message': message, 'recipient': phone_number})

    mocker.patch('cic_notify.api.Api.sms', mock_sms_api)
    mocker.patch('cic_ussd.notifications.Notifier.send_sms_notification', mock_send_sms_notification)
    return messages


@pytest.fixture(scope='function')
def mock_outgoing_transactions(mocker):
    transactions = []

    def mock_process_outgoing_transfer_transaction(self, amount: int, token_symbol: str = 'SRF'):
        transactions.append({
            'amount': amount,
            'token_symbol': token_symbol
        })

    mocker.patch(
        'cic_ussd.transactions.OutgoingTransactionProcessor.process_outgoing_transfer_transaction',
        mock_process_outgoing_transfer_transaction
    )
    return transactions


@pytest.fixture(scope='function')
def mock_balance(mocker):
    mocked_operational_balance = mocker.patch('cic_ussd.accounts.BalanceManager.get_balances')

    def _mock_operational_balance(balance: int):
        mocked_operational_balance.return_value = truncate(value=balance, decimals=2)

    return _mock_operational_balance
