# standard imports
import logging

# third-party imports
from sqlalchemy import Column, String

# local imports
from cic_ussd.db.models.base import SessionBase

logg = logging.getLogger(__name__)


class TaskTracker(SessionBase):
    __tablename__ = 'task_tracker'

    def __init__(self, task_uuid):
        self.task_uuid = task_uuid

    task_uuid = Column(String, nullable=False)
