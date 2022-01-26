# standard imports

# external imports
import celery

# local imports
from cic_notify.db.enum import NotificationStatusEnum, NotificationTransportEnum
from cic_notify.db.models.notification import Notification

# test imports
from tests.helpers.phone import phone_number


def test_persist_notification(celery_session_worker, init_database):
    message = 'Hello world.'
    recipient = phone_number()
    s_persist_notification = celery.signature(
        'cic_notify.tasks.sms.db.persist_notification', (message, recipient)
    )
    s_persist_notification.apply_async().get()

    notification = Notification.session.query(Notification).filter_by(recipient=recipient).first()
    assert notification.status == NotificationStatusEnum.UNKNOWN
    assert notification.recipient == recipient
    assert notification.message == message
    assert notification.transport == NotificationTransportEnum.SMS