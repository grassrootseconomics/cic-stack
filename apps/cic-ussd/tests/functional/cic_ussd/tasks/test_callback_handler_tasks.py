# standard imports
import json
import logging
from datetime import datetime

# third party imports
import celery
import pytest

# local imports
from cic_ussd.db.models.user import User
from cic_ussd.error import ActionDataNotFoundError
from cic_ussd.transactions import from_wei

logg = logging.getLogger()


def test_successful_process_account_creation_callback_task(account_creation_action_data,
                                                           celery_session_worker,
                                                           init_database,
                                                           init_redis_cache,
                                                           mocker,
                                                           set_account_creation_action_data):
    phone_number = account_creation_action_data.get('phone_number')
    task_id = account_creation_action_data.get('task_id')

    mocked_task_request = mocker.patch('celery.app.task.Task.request')

    # WARNING: [THE SETTING OF THE ROOT ID IS A HACK AND SHOULD BE REVIEWED OR IMPROVED]
    mocked_task_request.root_id = task_id

    user = init_database.query(User).filter_by(phone_number=phone_number).first()
    assert user is None

    redis_cache = init_redis_cache
    action_data = redis_cache.get(task_id)
    action_data = json.loads(action_data)

    assert action_data.get('status') == 'PENDING'

    status_code = 0
    result = '0x6315c185fd23bDbbba058E2a504197915aCC5065'
    url = ''

    s_process_callback_request = celery.signature(
        'cic_ussd.tasks.callback_handler.process_account_creation_callback',
        [result, url, status_code]
    )
    s_process_callback_request.apply_async().get()

    user = init_database.query(User).filter_by(phone_number=phone_number).first()
    assert user.blockchain_address == result

    action_data = redis_cache.get(task_id)
    action_data = json.loads(action_data)

    assert action_data.get('status') == 'CREATED'


def test_unsuccessful_process_account_creation_callback_task(init_database,
                                                             init_redis_cache,
                                                             celery_session_worker):
    with pytest.raises(ActionDataNotFoundError) as error:
        status_code = 0
        result = '0x6315c185fd23bDbbba058E2a504197915aCC5065'
        url = ''

        s_process_callback_request = celery.signature(
            'cic_ussd.tasks.callback_handler.process_account_creation_callback',
            [result, url, status_code]
        )
        result = s_process_callback_request.apply_async()
        task_id = result.get()

        assert str(error.value) == f'Account creation task: {task_id}, returned unexpected response: {status_code}'


def test_successful_token_gift_incoming_transaction(celery_session_worker,
                                                    create_activated_user,
                                                    mock_notifier_api,
                                                    set_locale_files,
                                                    successful_incoming_token_gift_callback):
    result = successful_incoming_token_gift_callback.get('RESULT')
    param = successful_incoming_token_gift_callback.get('PARAM')
    status_code = successful_incoming_token_gift_callback.get('STATUS_CODE')

    s_process_token_gift = celery.signature(
        'cic_ussd.tasks.callback_handler.process_incoming_transfer_callback',
        [result, param, status_code]
    )
    s_process_token_gift.apply_async().get()

    balance = from_wei(result.get('destination_value'))
    token_symbol = result.get('token_symbol')

    messages = mock_notifier_api

    assert messages[0].get('recipient') == create_activated_user.phone_number
    assert messages[0].get(
        'message') == f'Hello {""} you have been registered on Sarafu Network! Your balance is {balance} {token_symbol}. To use dial *483*46#. For help 0757628885.'


def test_successful_transfer_incoming_transaction(celery_session_worker,
                                                  create_valid_tx_sender,
                                                  create_valid_tx_recipient,
                                                  mock_notifier_api,
                                                  set_locale_files,
                                                  successful_incoming_transfer_callback):
    result = successful_incoming_transfer_callback.get('RESULT')
    param = successful_incoming_transfer_callback.get('PARAM')
    status_code = successful_incoming_transfer_callback.get('STATUS_CODE')

    s_process_token_gift = celery.signature(
        'cic_ussd.tasks.callback_handler.process_incoming_transfer_callback',
        [result, param, status_code]
    )
    s_process_token_gift.apply_async().get()

    value = result.get('destination_value')
    balance = ''
    token_symbol = result.get('token_symbol')

    sender_first_name = ''
    sender_last_name = ''
    phone_number = create_valid_tx_sender.phone_number
    tx_sender_information = f'{phone_number}, {sender_first_name}, {sender_last_name}'
    amount = from_wei(value=value)
    timestamp = datetime.now().strftime('%d-%m-%y, %H:%M %p')

    messages = mock_notifier_api

    assert messages[0].get('recipient') == create_valid_tx_recipient.phone_number
    assert messages[0].get(
        'message') == f'Successfully received {amount} {token_symbol} from {tx_sender_information} {timestamp}. New balance is {balance} {token_symbol}.'


def test_unsuccessful_incoming_transaction_recipient_not_found(celery_session_worker,
                                                               create_valid_tx_sender,
                                                               successful_incoming_transfer_callback):
    result = successful_incoming_transfer_callback.get('RESULT')
    param = successful_incoming_transfer_callback.get('PARAM')
    status_code = successful_incoming_transfer_callback.get('STATUS_CODE')

    with pytest.raises(ValueError) as error:
        s_process_token_gift = celery.signature(
            'cic_ussd.tasks.callback_handler.process_incoming_transfer_callback',
            [result, param, status_code]
        )
        s_process_token_gift.apply_async().get()

    recipient_blockchain_address = result.get('recipient')
    assert str(error.value) == f'Tx for recipient: {recipient_blockchain_address} was received but has no matching user in the system.'


def test_successful_incoming_transaction_sender_not_found(caplog,
                                                          celery_session_worker,
                                                          create_valid_tx_recipient,
                                                          successful_incoming_transfer_callback):
    result = successful_incoming_transfer_callback.get('RESULT')
    param = successful_incoming_transfer_callback.get('PARAM')
    status_code = successful_incoming_transfer_callback.get('STATUS_CODE')
    s_process_token_gift = celery.signature(
        'cic_ussd.tasks.callback_handler.process_incoming_transfer_callback',
        [result, param, status_code]
    )
    s_process_token_gift.apply_async().get()

    sender_blockchain_address = result.get('sender')
    assert 'Balance requires implementation of cic-eth integration with balance.' in caplog.text
    # assert f'Tx with sender: {sender_blockchain_address} was received but has no matching user in the system.\n' in caplog.text


def test_unsuccessful_incoming_transaction_invalid_status_code(celery_session_worker,
                                                               incoming_transfer_callback_invalid_tx_status_code):
    result = incoming_transfer_callback_invalid_tx_status_code.get('RESULT')
    param = incoming_transfer_callback_invalid_tx_status_code.get('PARAM')
    status_code = incoming_transfer_callback_invalid_tx_status_code.get('STATUS_CODE')

    with pytest.raises(ValueError) as error:
        s_process_token_gift = celery.signature(
            'cic_ussd.tasks.callback_handler.process_incoming_transfer_callback',
            [result, param, status_code]
        )
        s_process_token_gift.apply_async().get()

        assert str(error.value) == f'Unexpected status code: {status_code}'


def test_unsuccessful_incoming_transaction_invalid_param(celery_session_worker,
                                                         incoming_transfer_callback_invalid_tx_param):
    result = incoming_transfer_callback_invalid_tx_param.get('RESULT')
    param = incoming_transfer_callback_invalid_tx_param.get('PARAM')
    status_code = incoming_transfer_callback_invalid_tx_param.get('STATUS_CODE')

    with pytest.raises(ValueError) as error:
        s_process_token_gift = celery.signature(
            'cic_ussd.tasks.callback_handler.process_incoming_transfer_callback',
            [result, param, status_code]
        )
        s_process_token_gift.apply_async().get()

        assert str(error.value) == f'Unexpected transaction: param {status_code}'
