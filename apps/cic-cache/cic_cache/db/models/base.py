# third-party imports
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

Model = declarative_base(name='Model')


class SessionBase(Model):
    __abstract__ = True
 
    id = Column(Integer, primary_key=True)

    engine = None
    query = None
    sessionmaker = None


    @staticmethod
    def create_session():
        #SessionBase.session = session()
        #return SessionBase.session
        return SessionBase.sessionmaker()


    @staticmethod
    def _set_engine(engine):
        SessionBase.engine = engine
        SessionBase.sessionmaker = sessionmaker(bind=SessionBase.engine)


    @staticmethod
    def build():
        Model.metadata.create_all(bind=SessionBase.engine)


    @staticmethod
    def connect(dsn):
        e = create_engine(dsn)
        SessionBase._set_engine(e)


    @staticmethod
    def disconnect():
        SessionBase.engine.dispose()
        SessionBase.session = None
        SessionBase.engine = None
