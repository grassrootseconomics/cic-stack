# standard imports
import logging
import os

# external imports
import pytest
import requests_mock


# local imports
from cic_notify.error import NotInitializedError, AlreadyInitializedError, NotificationSendError
from cic_notify.tasks.sms.africastalking import AfricasTalkingNotifier

# test imports
from tests.helpers.phone import phone_number


def test_africas_talking_notifier(africastalking_response, caplog):
    caplog.set_level(logging.DEBUG)
    with pytest.raises(NotInitializedError) as error:
        AfricasTalkingNotifier()
    assert str(error.value) == ''

    api_key = os.urandom(24).hex()
    sender_id = 'bar'
    username = 'sandbox'
    AfricasTalkingNotifier.initialize(username, api_key, sender_id)
    africastalking_notifier = AfricasTalkingNotifier()
    assert africastalking_notifier.sender_id == sender_id
    assert africastalking_notifier.initiated is True

    with pytest.raises(AlreadyInitializedError) as error:
        AfricasTalkingNotifier.initialize(username, api_key, sender_id)
    assert str(error.value) == ''

    with requests_mock.Mocker(real_http=False) as request_mocker:
        message = 'Hello world.'
        recipient = phone_number()
        africastalking_response.get('SMSMessageData').get('Recipients')[0]['number'] = recipient
        request_mocker.register_uri(method='POST',
                                    headers={'content-type': 'application/json'},
                                    json=africastalking_response,
                                    url='https://api.sandbox.africastalking.com/version1/messaging',
                                    status_code=200)
        africastalking_notifier.send(message, recipient)
        assert f'Africastalking response sender-id {africastalking_response}' in caplog.text
        africastalking_notifier.sender_id = None
        africastalking_notifier.send(message, recipient)
        assert f'africastalking response no-sender-id {africastalking_response}' in caplog.text
        with pytest.raises(NotificationSendError) as error:
            status = 'InvalidPhoneNumber'
            status_code = 403
            africastalking_response.get('SMSMessageData').get('Recipients')[0]['status'] = status
            africastalking_response.get('SMSMessageData').get('Recipients')[0]['statusCode'] = status_code

            request_mocker.register_uri(method='POST',
                                        headers={'content-type': 'application/json'},
                                        json=africastalking_response,
                                        url='https://api.sandbox.africastalking.com/version1/messaging',
                                        status_code=200)
            africastalking_notifier.send(message, recipient)
        assert str(error.value) == f'Sending notification failed due to: {status}'
        with pytest.raises(NotificationSendError) as error:
            recipients = []
            status = 'InsufficientBalance'
            africastalking_response.get('SMSMessageData')['Recipients'] = recipients
            africastalking_response.get('SMSMessageData')['Message'] = status

            request_mocker.register_uri(method='POST',
                                        headers={'content-type': 'application/json'},
                                        json=africastalking_response,
                                        url='https://api.sandbox.africastalking.com/version1/messaging',
                                        status_code=200)
            africastalking_notifier.send(message, recipient)
        assert str(error.value) == f'Unexpected number of recipients: {len(recipients)}. Status: {status}'
