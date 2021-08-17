# standard imports
import logging
import os
import pytest
import shutil
import tempfile

# external imports
from celery import uuid


logg = logging.getLogger()


@pytest.fixture(scope='session')
def celery_includes():
    return [
        'cic_ussd.tasks.callback_handler',
        'cic_ussd.tasks.metadata',
        'cic_ussd.tasks.notifications',
        'cic_ussd.tasks.processor',
        'cic_ussd.tasks.ussd_session',
        'cic_eth.queue.balance',
        'cic_notify.tasks.sms',
    ]


@pytest.fixture(scope='session')
def celery_config():
    bq = tempfile.mkdtemp()
    bp = tempfile.mkdtemp()
    rq = tempfile.mkdtemp()
    logg.debug('celery broker queue {} processed {}'.format(bq, bp))
    logg.debug('celery backend store {}'.format(rq))
    yield {
        'broker_url': 'filesystem://',
        'broker_transport_options': {
            'data_folder_in': bq,
            'data_folder_out': bq,
            'data_folder_processed': bp,
        },
        'result_backend': 'file://{}'.format(rq),
    }
    logg.debug('cleaning up celery filesystem backend files {} {} {}'.format(bq, bp, rq))
    shutil.rmtree(bq)
    shutil.rmtree(bp)
    shutil.rmtree(rq)


@pytest.fixture(scope='session')
def celery_enable_logging():
    return True


@pytest.fixture(scope='function')
def task_uuid():
    return uuid()
