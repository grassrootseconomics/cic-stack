"""API for cic-cache celery tasks

.. moduleauthor:: Louis Holbrook <dev@holbrook.no>

"""
# standard imports
import logging

# third-party imports 
import celery


app = celery.current_app

logg = logging.getLogger(__name__)


class Api:
    """Creates task chains to perform well-known CIC operations.

    Each method that sends tasks returns details about the root task. The root task uuid can be provided in the callback, to enable to caller to correlate the result with individual calls. It can also be used to independently poll the completion of a task chain.

    :param callback_param: Static value to pass to callback
    :type callback_param: str
    :param callback_task: Callback task that executes callback_param call. (Must be included by the celery worker)
    :type callback_task: string
    :param queue: Name of worker queue to submit tasks to
    :type queue: str
    """
    def __init__(self, queue='cic-cache', callback_param=None, callback_task='cic_cache.callbacks.noop.noop', callback_queue=None):
        self.callback_param = callback_param
        self.callback_task = callback_task
        self.queue = queue
        logg.info('api using queue {}'.format(self.queue))
        self.callback_success = None
        self.callback_error = None
        if callback_queue == None:
            callback_queue=self.queue

        if callback_param != None:
            self.callback_success = celery.signature(
                    callback_task,
                    [
                        callback_param,
                        0,
                        ],
                    queue=callback_queue,
                    )
            self.callback_error = celery.signature(
                    callback_task,
                    [
                        callback_param,
                        1,
                        ],
                    queue=callback_queue,
                    )       

    def list(self, offset, limit, address=None):
        s = celery.signature(
        'cic_cache.tasks.tx.tx_filter',
        [
            0,
            100,
            address,
            ],
            queue=None
        )
        if self.callback_param != None:
            s.link(self.callback_success).on_error(self.callback_error)

        t = s.apply_async()

        return t
