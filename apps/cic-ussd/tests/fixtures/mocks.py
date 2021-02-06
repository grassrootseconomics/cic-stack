# standard imports

# third-party imports
import pytest

# local imports
from cic_ussd.translation import translation_for
from cic_ussd.transactions import truncate


@pytest.fixture(scope='function', autouse=True)
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
    mocked_operational_balance = mocker.patch('cic_ussd.accounts.BalanceManager.get_operational_balance')

    def _mock_operational_balance(balance: int):
        mocked_operational_balance.return_value = truncate(value=balance, decimals=2)

    return _mock_operational_balance
