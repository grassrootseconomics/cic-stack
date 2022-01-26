# standard imports

# external imports
import celery

# local imports
from cic_notify.api import Api

# test imports
from tests.helpers.phone import phone_number


def test_api(celery_session_worker, mocker):
    mocked_group = mocker.patch('celery.group')
    message = 'Hello world.'
    recipient = phone_number()
    s_send = celery.signature('cic_notify.tasks.sms.africastalking.send', [message, recipient], queue=None)
    s_log = celery.signature('cic_notify.tasks.sms.log.log', [message, recipient], queue=None)
    s_persist_notification = celery.signature(
        'cic_notify.tasks.sms.db.persist_notification', [message, recipient], queue=None)
    signatures = [s_send, s_log, s_persist_notification]
    api = Api(queue=None)
    api.sms(message, recipient)
    mocked_group.assert_called_with(signatures)
