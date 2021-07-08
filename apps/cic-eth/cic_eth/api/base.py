# standard imports
import logging

# external imports
import celery
from chainlib.chain import ChainSpec

logg = logging.getLogger(__name__)

class ApiBase:
    """Creates task chains to perform well-known CIC operations.

    Each method that sends tasks returns details about the root task. The root task uuid can be provided in the callback, to enable to caller to correlate the result with individual calls. It can also be used to independently poll the completion of a task chain.

    :param callback_param: Static value to pass to callback
    :type callback_param: str
    :param callback_task: Callback task that executes callback_param call. (Must be included by the celery worker)
    :type callback_task: string
    :param queue: Name of worker queue to submit tasks to
    :type queue: str
    """
    def __init__(self, chain_str, queue='cic-eth', callback_param=None, callback_task='cic_eth.callbacks.noop.noop', callback_queue=None):
        self.chain_str = chain_str
        self.chain_spec = ChainSpec.from_chain_str(chain_str)
        self.callback_param = callback_param
        self.callback_task = callback_task
        self.queue = queue
        logg.debug('api using queue {}'.format(self.queue))
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


