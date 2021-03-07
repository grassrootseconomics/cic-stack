# import
import requests

# external imports
import celery
import sqlalchemy

# local imports
from cic_eth.error import (
        SignerError,
        EthError,
        )


class CriticalTask(celery.Task):
    retry_jitter = True
    retry_backoff = True
    retry_backoff_max = 8


class CriticalSQLAlchemyTask(CriticalTask):
    autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
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
        EthError,
        )

class CriticalSQLAlchemyAndSignerTask(CriticalTask):
     autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
        SignerError,
        ) 

class CriticalWeb3AndSignerTask(CriticalTask):
    autoretry_for = (
        requests.exceptions.ConnectionError,
        SignerError,
        )
