# import
import time
import requests
import logging
import uuid

# external imports
import celery
import sqlalchemy

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

    def create_session(self):
        logg.warning('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> session from base {}'.format(id(self.session_func)))
        return BaseTask.session_func()

    
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


class CriticalSQLAlchemyAndWeb3Task(CriticalTask):
    autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
        requests.exceptions.ConnectionError,
        sqlalchemy.exc.ResourceClosedError,
        EthError,
        )

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


@celery_app.task(bind=True, base=BaseTask)
def hello(self):
    time.sleep(0.1)
    return id(SessionBase.create_session)
