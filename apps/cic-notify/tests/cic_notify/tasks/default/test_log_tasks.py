# standard imports
import logging

# external imports
import celery

# local imports

# test imports
from tests.helpers.phone import phone_number


def test_log(caplog, celery_session_worker):
    message = 'Hello world.'
    recipient = phone_number()
    caplog.set_level(logging.INFO)
    s_log = celery.signature(
        'cic_notify.tasks.default.log.log', [message, recipient]
    )
    s_log.apply_async().get()
    assert f'message to {recipient}: {message}' in caplog.text
