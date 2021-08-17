# standard imports
import logging

# third-party imports
import celery
import sqlalchemy

# local imports
from cic_ussd.error import MetadataStoreError
from cic_ussd.db.models.base import SessionBase

logg = logging.getLogger(__name__)


class BaseTask(celery.Task):

    session_func = SessionBase.create_session

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


class CriticalMetadataTask(CriticalTask):
    autoretry_for = (
        MetadataStoreError,
    )
