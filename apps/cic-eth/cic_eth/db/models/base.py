# stanard imports
import logging

# third-party imports
from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import (
        StaticPool,
        QueuePool,
        AssertionPool,
        NullPool,
        )

logg = logging.getLogger()

Model = declarative_base(name='Model')


class SessionBase(Model):
    """The base object for all SQLAlchemy enabled models. All other models must extend this.
    """
    __abstract__ = True
 
    id = Column(Integer, primary_key=True)

    engine = None
    """Database connection engine of the running aplication"""
    sessionmaker = None
    """Factory object responsible for creating sessions from the  connection pool"""
    transactional = True
    """Whether the database backend supports query transactions. Should be explicitly set by initialization code"""
    poolable = True
    """Whether the database backend supports connection pools. Should be explicitly set by initialization code"""
    procedural = True
    """Whether the database backend supports stored procedures"""
    localsessions = {}
    """Contains dictionary of sessions initiated by db model components"""


    @staticmethod
    def create_session():
        """Creates a new database session.
        """
        return SessionBase.sessionmaker()


    @staticmethod
    def _set_engine(engine):
        """Sets the database engine static property
        """
        SessionBase.engine = engine
        SessionBase.sessionmaker = sessionmaker(bind=SessionBase.engine)


    @staticmethod
    def connect(dsn, pool_size=16, debug=False):
        """Create new database connection engine and connect to database backend.

        :param dsn: DSN string defining connection.
        :type dsn: str
        """
        e = None
        if SessionBase.poolable:
            poolclass = QueuePool
            if pool_size > 1:
                logg.info('db using queue pool')
                e = create_engine(
                        dsn,
                        max_overflow=pool_size*3,
                        pool_pre_ping=True,
                        pool_size=pool_size,
                        pool_recycle=60,
                        poolclass=poolclass,
                        echo=debug,
                    )
            else:
                if pool_size == 0:
                    logg.info('db using nullpool')
                    poolclass = NullPool
                elif debug:
                    logg.info('db using assertion pool')
                    poolclass = AssertionPool
                else:
                    logg.info('db using static pool')
                    poolclass = StaticPool
                e = create_engine(
                        dsn,
                        poolclass=poolclass,
                        echo=debug,
                    )
        else:
            logg.info('db not poolable')
            e = create_engine(
                    dsn,
                    echo=debug,
                    )

        SessionBase._set_engine(e)


    @staticmethod
    def disconnect():
        """Disconnect from database and free resources.
        """
        SessionBase.engine.dispose()
        SessionBase.engine = None


    @staticmethod
    def bind_session(session=None):
        localsession = session
        if localsession == None:
            localsession = SessionBase.create_session()
            localsession_key = str(id(localsession))
            logg.debug('creating new session {}'.format(localsession_key))
            SessionBase.localsessions[localsession_key] = localsession
        return localsession


    @staticmethod
    def release_session(session=None):
        session_key = str(id(session))
        if SessionBase.localsessions.get(session_key) != None:
            logg.debug('commit and destroy session {}'.format(session_key))
            session.commit()
            session.close()
            del SessionBase.localsessions[session_key]
