# standard imports
import datetime
import logging

# external imports
from sqlalchemy import Column, String, DateTime

# local imports
from .base import SessionBase


class Debug(SessionBase):

    __tablename__ = 'debug'

    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    tag = Column(String)
    description = Column(String)


    def __init__(self, tag, description):
        self.tag = tag
        self.description = description
