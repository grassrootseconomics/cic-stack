# standard imports

# external imports
from faker import Faker
from faker_e164.providers import E164Provider

# local imports
from cic_notify.db.enum import NotificationStatusEnum, NotificationTransportEnum
from cic_notify.db.models.notification import Notification


# test imports
from tests.helpers.phone import phone_number


def test_notification(init_database):
    message = 'Hello world'
    recipient = phone_number()
    notification = Notification(NotificationTransportEnum.SMS, recipient, message)
    init_database.add(notification)
    init_database.commit()

    notification = init_database.query(Notification).get(1)
    assert notification.status == NotificationStatusEnum.UNKNOWN
    assert notification.recipient == recipient
    assert notification.message == message
    assert notification.transport == NotificationTransportEnum.SMS
