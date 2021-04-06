# standard imports
import logging
import re

# third-party imports
from celery.app.control import Inspect
import celery

# local imports
from cic_notify.tasks import sms

app = celery.current_app
logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()

sms_tasks_matcher = r"^(cic_notify.tasks.sms)(\.\w+)?"


re_q = r'^cic-notify'
def get_sms_queue_tasks(app, task_prefix='cic_notify.tasks.sms.'):
    host_queues = []

    i = Inspect(app=app)
    qs = i.active_queues()
    for host in qs.keys():
        for q in qs[host]:
            if re.match(re_q, q['name']):
                host_queues.append((host, q['name'],))
   
    task_prefix_len = len(task_prefix)
    queue_tasks = []
    for (host, queue) in host_queues:
        i = Inspect(app=app, destination=[host])
        for tasks in i.registered_tasks().values():
            for task in tasks:
                logg.debug('q {}'.format(task))
                if len(task) >= task_prefix_len and task[:task_prefix_len] == task_prefix:
                    queue_tasks.append((queue, task,))
    
    return queue_tasks


class Api:
    # TODO: Implement callback strategy
    def __init__(self, queue='cic-notify'):
        """
        :param queue: The queue on which to execute notification tasks
        :type queue: str
        """
        self.sms_tasks = get_sms_queue_tasks(app)
        logg.debug('sms tasks {}'.format(self.sms_tasks))


    def sms(self, message, recipient):
        """This function chains all sms tasks in order to send a message, log and persist said data to disk
        :param message: The message to be sent to the recipient.
        :type message: str
        :param recipient: The phone number of the recipient.
        :type recipient: str
        :return: a celery Task
        :rtype: Celery.Task
        """
        signatures = []
        for q in self.sms_tasks:
            signature = celery.signature(
                    q[1],
                    [
                        message,
                        recipient,
                        ],
                    queue=q[0],
                    )
            signatures.append(signature)

        t = celery.group(signatures)()

        return t
