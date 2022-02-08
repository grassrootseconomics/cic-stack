# standard imports
import logging

# external imports
import celery

# local imports
from cic_notify.mux import Muxer

logg = logging.getLogger()
celery_app = celery.current_app


@celery_app.task
def resolve_tasks(channel_keys, message, queue, recipient):
    muxer = Muxer()
    muxer.route(channel_keys=channel_keys)

    signatures = []
    for task in muxer.tasks:
        signature = celery.signature(task, [message, recipient, ], queue=queue)
        signatures.append(signature)
    return celery.group(signatures)()
