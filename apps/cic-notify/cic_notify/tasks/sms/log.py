# standard imports
import logging
import time

# third-party imports
import celery

celery_app = celery.current_app
logg = celery_app.log.get_default_logger()
local_logg = logging.getLogger(__name__)


@celery_app.task
def log(recipient, message):
    """
    :param recipient:
    :type recipient:
    :param message:
    :type message:
    :return:
    :rtype:
    """
    timestamp = time.time()
    log_string = f'[{timestamp}] {__name__} message to {recipient}: {message}'
    logg.info(log_string)
    local_logg.info(log_string)
