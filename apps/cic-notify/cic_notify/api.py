# standard imports
import logging
import re

# third-party imports
import cic_notify.tasks.sms.db
from celery.app.control import Inspect
import celery

# local imports
from cic_notify.tasks import sms

app = celery.current_app
logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


class Api:
    def __init__(self, queue: any = 'cic-notify'):
        """
        :param queue: The queue on which to execute notification tasks
        :type queue: str
        """
        self.queue = queue

    def sms(self, message: str, recipient: str):
        """This function chains all sms tasks in order to send a message, log and persist said data to disk
        :param message: The message to be sent to the recipient.
        :type message: str
        :param recipient: The phone number of the recipient.
        :type recipient: str
        :return: a celery Task
        :rtype: Celery.Task
        """
        s_send = celery.signature('cic_notify.tasks.sms.africastalking.send', [message, recipient], queue=self.queue)
        s_log = celery.signature('cic_notify.tasks.sms.log.log', [message, recipient], queue=self.queue)
        s_persist_notification = celery.signature(
            'cic_notify.tasks.sms.db.persist_notification', [message, recipient], queue=self.queue)
        signatures = [s_send, s_log, s_persist_notification]
        return celery.group(signatures)()
