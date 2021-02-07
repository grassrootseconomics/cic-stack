# standard imports

# third-party imports
import celery

# local imports
from cic_notify.db.models.notification import Notification
from cic_notify.db.enum import NotificationTransportEnum

celery_app = celery.current_app


@celery_app.task
def persist_notification(recipient, message):
    """
    :param recipient:
    :type recipient:
    :param message:
    :type message:
    :return:
    :rtype:
    """
    Notification.create_session()
    notification = Notification(transport=NotificationTransportEnum.SMS, recipient=recipient, message=message)
    Notification.session.add(notification)
    Notification.session.commit()
