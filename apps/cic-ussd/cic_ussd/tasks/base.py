# standard imports

# third-party imports
import celery
import sqlalchemy

# local imports
from cic_ussd.error import MetadataStoreError


class CriticalTask(celery.Task):
    retry_jitter = True
    retry_backoff = True
    retry_backoff_max = 8


class CriticalSQLAlchemyTask(CriticalTask):
    autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
    )


class CriticalMetadataTask(CriticalTask):
    autoretry_for = (
        MetadataStoreError,
    )
