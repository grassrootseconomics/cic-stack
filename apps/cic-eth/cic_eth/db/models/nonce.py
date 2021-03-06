# standard imports
import logging
import datetime

# third-party imports
from sqlalchemy import Column, String, Integer, DateTime

# local imports
from .base import SessionBase
from cic_eth.error import (
        InitializationError,
        IntegrityError,
        )

logg = logging.getLogger()


class Nonce(SessionBase):
    """Provides thread-safe nonce increments.
    """
    __tablename__ = 'nonce'

    nonce = Column(Integer)
    address_hex = Column(String(42))


    @staticmethod
    def get(address, session=None):
        session = SessionBase.bind_session(session)

        q = session.query(Nonce)
        q = q.filter(Nonce.address_hex==address)
        nonce = q.first()

        nonce_value = None
        if nonce != None:
            nonce_value = nonce.nonce;

        SessionBase.release_session(session)

        return nonce_value


    @staticmethod
    def __get(conn, address):
        r = conn.execute("SELECT nonce FROM nonce WHERE address_hex = '{}'".format(address))
        nonce = r.fetchone()
        if nonce == None:
            return None
        return nonce[0]


    @staticmethod
    def __set(conn, address, nonce):
        conn.execute("UPDATE nonce set nonce = {} WHERE address_hex = '{}'".format(nonce, address))


    @staticmethod
    def __init(conn, address, nonce):
        conn.execute("INSERT INTO nonce (nonce, address_hex) VALUES ({}, '{}')".format(nonce, address))


    @staticmethod
    def init(address, nonce=0, session=None):
        session = SessionBase.bind_session(session)

        q = session.query(Nonce)
        q = q.filter(Nonce.address_hex==address)
        o = q.first()
        if o != None:
            session.flush()
            raise InitializationError('nonce on {} already exists ({})'.format(address, o.nonce))
        session.flush()
        Nonce.__init(session, address, nonce)

        SessionBase.release_session(session)


    # TODO: Incrementing nonce MUST be done by separate tasks.
    @staticmethod
    def next(address, initial_if_not_exists=0):
        """Generate next nonce for the given address.

        If there is no previous nonce record for the address, the nonce may be initialized to a specified value, or 0 if no value has been given.

        :param address: Associate Ethereum address 
        :type address: str, 0x-hex
        :param initial_if_not_exists: Initial nonce value to set if no record exists
        :type initial_if_not_exists: number
        :returns: Nonce
        :rtype: number
        """
        #session = SessionBase.bind_session(session)
        
        #session.begin_nested()
        conn = Nonce.engine.connect()
        if Nonce.transactional:
            conn.execute('BEGIN')
            conn.execute('LOCK TABLE nonce IN SHARE ROW EXCLUSIVE MODE')
            logg.debug('locking nonce table for address {}'.format(address))
        nonce = Nonce.__get(conn, address)
        logg.debug('get nonce {} for address {}'.format(nonce, address))
        if nonce == None:
            nonce = initial_if_not_exists
            logg.debug('setting default nonce to {} for address {}'.format(nonce, address))
            Nonce.__init(conn, address, nonce)
        Nonce.__set(conn, address, nonce+1)
        if Nonce.transactional:
            conn.execute('COMMIT')
            logg.debug('unlocking nonce table for address {}'.format(address))
        conn.close()
        #session.commit()

        #SessionBase.release_session(session)
        return nonce


class NonceReservation(SessionBase):

    __tablename__ = 'nonce_task_reservation'

    nonce = Column(Integer)
    key = Column(String)
    date_created = Column(DateTime, default=datetime.datetime.utcnow)


    @staticmethod
    def peek(key, session=None):
        session = SessionBase.bind_session(session)

        q = session.query(NonceReservation)
        q = q.filter(NonceReservation.key==key)
        o = q.first()

        nonce = None
        if o != None:
            nonce = o.nonce

        session.flush()

        SessionBase.release_session(session)

        return nonce


    @staticmethod
    def release(key, session=None):

        session = SessionBase.bind_session(session)

        nonce = NonceReservation.peek(key, session=session)

        q = session.query(NonceReservation)
        q = q.filter(NonceReservation.key==key)
        o = q.first()

        if o == None:
            raise IntegrityError('nonce for key {}'.format(nonce))
            SessionBase.release_session(session)

        session.delete(o)
        session.flush()

        SessionBase.release_session(session)

        return nonce


    @staticmethod
    def next(address, key, session=None):
        session = SessionBase.bind_session(session)

        if NonceReservation.peek(key, session) != None:
            raise IntegrityError('nonce for key {}'.format(key))

        nonce = Nonce.next(address)

        o = NonceReservation()
        o.nonce = nonce
        o.key = key
        session.add(o)
       
        SessionBase.release_session(session)

        return nonce
