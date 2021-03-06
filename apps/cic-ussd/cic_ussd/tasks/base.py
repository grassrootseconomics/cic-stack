# standard imports

# third-party imports
import celery
import sqlalchemy

# local imports


class CriticalTask(celery.Task):
    retry_jitter = True
    retry_backoff = True
    retry_backoff_max = 8


class CriticalSQLAlchemyTask(CriticalTask):
    autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
    )
