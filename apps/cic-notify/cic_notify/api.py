# standard imports
import logging

# external imports
import celery

# local imports


app = celery.current_app
logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


class Api:
    def __init__(self, channel_keys=None, queue: any = 'cic-notify'):
        """
        :param queue: The queue on which to execute notification tasks.
        :type queue: str
        """
        if channel_keys is None:
            channel_keys = []
        self.channel_keys = channel_keys
        self.queue = queue

    def notify(self, message: str, recipient: str):
        """
        :param message:
        :type message:
        :param recipient:
        :type recipient:
        :return:
        :rtype:
        """
        signature = celery.signature(
            'cic_notify.tasks.default.resolver.resolve_tasks',
            [self.channel_keys, message, self.queue, recipient], queue=self.queue)
        signature.apply_async()
