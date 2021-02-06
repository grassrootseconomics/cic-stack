# standard imports
import datetime

# third-party imports
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Model = declarative_base(name='Model')


class SessionBase(Model):
    __abstract__ = True

    id = Column(Integer, primary_key=True)
    created = Column(DateTime, default=datetime.datetime.utcnow)
    updated = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    engine = None
    session = None
    query = None

    @staticmethod
    def create_session():
        session = sessionmaker(bind=SessionBase.engine)
        return session()

    @staticmethod
    def _set_engine(engine):
        SessionBase.engine = engine

    @staticmethod
    def build():
        Model.metadata.create_all(bind=SessionBase.engine)

    @staticmethod
    # https://docs.sqlalchemy.org/en/13/core/pooling.html#pool-disconnects
    def connect(data_source_name):
        engine = create_engine(data_source_name, pool_pre_ping=True)
        SessionBase._set_engine(engine)

    @staticmethod
    def disconnect():
        SessionBase.engine.dispose()
        SessionBase.engine = None

