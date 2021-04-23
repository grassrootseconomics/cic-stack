# import
import time
import requests
import logging
import uuid

# external imports
import celery
import sqlalchemy
from chainlib.eth.constant import ZERO_ADDRESS
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import RPCGasOracle

# local imports
from cic_eth.error import (
        SignerError,
        EthError,
        )
from cic_eth.db.models.base import SessionBase

logg = logging.getLogger(__name__)

celery_app = celery.current_app


class BaseTask(celery.Task):

    session_func = SessionBase.create_session
    call_address = ZERO_ADDRESS
    create_nonce_oracle = RPCNonceOracle
    create_gas_oracle = RPCGasOracle
    default_token_address = None
    default_token_symbol = None

    def create_session(self):
        return BaseTask.session_func()


    def log_banner(self):
        logg.debug('task {} root uuid {}'.format(self.__class__.__name__, self.request.root_id))
        return

    
class CriticalTask(BaseTask):
    retry_jitter = True
    retry_backoff = True
    retry_backoff_max = 8


class CriticalSQLAlchemyTask(CriticalTask):
    autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
        sqlalchemy.exc.ResourceClosedError,
        ) 


class CriticalWeb3Task(CriticalTask):
    autoretry_for = (
        requests.exceptions.ConnectionError,
        )
    safe_gas_threshold_amount = 2000000000 * 60000 * 3
    safe_gas_refill_amount = safe_gas_threshold_amount * 5 


class CriticalSQLAlchemyAndWeb3Task(CriticalTask):
    autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
        requests.exceptions.ConnectionError,
        sqlalchemy.exc.ResourceClosedError,
        EthError,
        )
    safe_gas_threshold_amount = 2000000000 * 60000 * 3
    safe_gas_refill_amount = safe_gas_threshold_amount * 5 


class CriticalSQLAlchemyAndSignerTask(CriticalTask):
     autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
        sqlalchemy.exc.ResourceClosedError,
        SignerError,
        ) 

class CriticalWeb3AndSignerTask(CriticalTask):
    autoretry_for = (
        requests.exceptions.ConnectionError,
        SignerError,
        )
    safe_gas_threshold_amount = 2000000000 * 60000 * 3
    safe_gas_refill_amount = safe_gas_threshold_amount * 5 


@celery_app.task(bind=True, base=BaseTask)
def hello(self):
    time.sleep(0.1)
    return id(SessionBase.create_session)


@celery_app.task()
def check_health(self):
    celery.app.control.shutdown()
