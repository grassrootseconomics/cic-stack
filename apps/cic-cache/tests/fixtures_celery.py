# third-party imports
import pytest
import tempfile
import logging
import shutil

logg = logging.getLogger(__name__)


# celery fixtures
@pytest.fixture(scope='session')
def celery_includes():
    return [
        'cic_cache.tasks.tx',
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
def celery_worker_parameters():
    return {
#            'queues': ('cic-cache'),
            }

@pytest.fixture(scope='session')
def celery_enable_logging():
    return True
