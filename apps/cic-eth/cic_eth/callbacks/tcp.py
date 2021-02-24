# standard imports
import socket
import logging
import json

# third-party imports
import celery

# local imports
from . import Callback

celery_app = celery.current_app

logg = celery_app.log.get_default_logger()


@celery_app.task(base=Callback, bind=True)
def tcp(self, result, destination, status_code):
    s = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)
    (host, port) = destination.split(':')
    logg.debug('tcp callback to {} {}'.format(host, port))
    s.connect((host, int(port)))
    data = {
            'root_id': self.request.root_id,
            'status': status_code,
            'result': result,
            }
    s.send(json.dumps(data).encode('utf-8'))
    s.close()
