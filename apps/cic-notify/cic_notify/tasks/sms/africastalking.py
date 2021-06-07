# standard imports
import logging

# third party imports
import celery
import africastalking

# local imports
from cic_notify.error import NotInitializedError, AlreadyInitializedError, NotificationSendError
from cic_notify.ext.enums import AfricasTalkingStatusCodes

logg = logging.getLogger()
celery_app = celery.current_app


class AfricasTalkingNotifier:
    initiated = None
    sender_id = None

    def __init__(self):
        if not self.initiated:
            raise NotInitializedError()
        self.api_client = africastalking.SMS

    @staticmethod
    def initialize(api_username, api_key, sender_id=None):
        """
        :param api_username:
        :type api_username:
        :param api_key:
        :type api_key:
        :param sender_id:
        :type sender_id:
        """
        if AfricasTalkingNotifier.initiated:
            raise AlreadyInitializedError()
        africastalking.initialize(username=api_username, api_key=api_key)

        AfricasTalkingNotifier.sender_id = sender_id
        AfricasTalkingNotifier.initiated = True

    def send(self, message, recipient):
        """
        :param message:
        :type message:
        :param recipient:
        :type recipient:
        :return:
        :rtype:
        """
        if self.sender_id:
            response = self.api_client.send(message=message, recipients=[recipient], sender_id=self.sender_id)
            logg.debug(f'Africastalking response sender-id {response}')

        else:
            response = self.api_client.send(message=message, recipients=[recipient])
            logg.debug(f'africastalking response no-sender-id {response}')

        recipients = response.get('SMSMessageData').get('Recipients')

        if len(recipients) != 1:
            status = response.get('SMSMessageData').get('Message')
            raise NotificationSendError(f'Unexpected number of recipients: {len(recipients)}. Status: {status}')

        status_code = recipients[0].get('statusCode')
        status = recipients[0].get('status')

        if status_code not in [
            AfricasTalkingStatusCodes.PROCESSED.value,
            AfricasTalkingStatusCodes.SENT.value,
            AfricasTalkingStatusCodes.QUEUED.value
        ]:
            raise NotificationSendError(f'Sending notification failed due to: {status}')


@celery_app.task
def send(message, recipient):
    """
    :param message:
    :type message:
    :param recipient:
    :type recipient:
    :return:
    :rtype:
    """
    africastalking_notifier = AfricasTalkingNotifier()
    africastalking_notifier.send(message=message, recipient=recipient)
