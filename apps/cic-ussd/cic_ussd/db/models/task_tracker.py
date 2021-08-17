# standard imports
import logging

# third-party imports
from sqlalchemy import Column, String
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.db.models.base import SessionBase

logg = logging.getLogger(__name__)


class TaskTracker(SessionBase):
    __tablename__ = 'task_tracker'

    def __init__(self, task_uuid):
        self.task_uuid = task_uuid

    task_uuid = Column(String, nullable=False)

    @staticmethod
    def add(session: Session, task_uuid: str):
        """This function persists celery tasks uuids to storage.
        :param session: Database session object.
        :type session: Session
        :param task_uuid: The uuid for an initiated task.
        :type task_uuid: str
        """
        session = SessionBase.bind_session(session=session)
        task_record = TaskTracker(task_uuid=task_uuid)
        session.add(task_record)
        session.flush()
        SessionBase.release_session(session=session)
