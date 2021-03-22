# external imports
import pytest
import tempfile
import logging
import shutil

# local impors
from cic_eth.task import BaseTask

#logg = logging.getLogger(__name__)
logg = logging.getLogger()


@pytest.fixture(scope='function')
def init_celery_tasks(
    contract_roles, 
        ):
    BaseTask.call_address = contract_roles['DEFAULT']


# celery fixtures
@pytest.fixture(scope='session')
def celery_includes():
    return [
#        'cic_eth.eth.bancor',
        'cic_eth.eth.erc20',
        'cic_eth.eth.tx',
        'cic_eth.ext.tx',
        'cic_eth.queue.tx',
        'cic_eth.queue.balance',
        'cic_eth.admin.ctrl',
        'cic_eth.admin.nonce',
        'cic_eth.admin.debug',
        'cic_eth.eth.account',
        'cic_eth.callbacks.noop',
        'cic_eth.callbacks.http',
        'tests.mock.filter',
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
#            'queues': ('celery'),
            }

@pytest.fixture(scope='session')
def celery_enable_logging():
    return True
