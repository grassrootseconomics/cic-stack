# standard imports
import logging
import pytest
import shutil
import tempfile

logg = logging.getLogger()


@pytest.fixture(scope='session')
def celery_includes():
    return [
        'cic_ussd.tasks.ussd',
        'cic_ussd.tasks.callback_handler',
        'cic_notify.tasks.sms',
        'cic_ussd.tasks.metadata'
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
