# third-party imports
import celery
import logging

celery_app = celery.current_app
logg = logging.getLogger()


@celery_app.task()
def log_it_plz(whatever):
    logg.info('logged it plz: {}'.format(whatever)) 
