# external imports
import celery
import sqlalchemy


class CriticalSQLAlchemyTask(celery.Task):
    autoretry_for = (
        sqlalchemy.exc.DatabaseError,
        sqlalchemy.exc.TimeoutError,
        ) 
    retry_jitter = True
    retry_backoff = True
    retry_backoff_max = 8
