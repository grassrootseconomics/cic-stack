# standard imports
import logging

# third-party imports
from sqlalchemy import Column, String, Integer

# local imports
from .base import SessionBase

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
    def __get(session, address):
        r = session.execute("SELECT nonce FROM nonce WHERE address_hex = '{}'".format(address))
        nonce = r.fetchone()
        session.flush()
        if nonce == None:
            return None
        return nonce[0]


    @staticmethod
    def __set(session, address, nonce):
        session.execute("UPDATE nonce set nonce = {} WHERE address_hex = '{}'".format(nonce, address))
        session.flush()


    @staticmethod
    def next(address, initial_if_not_exists=0, session=None):
        """Generate next nonce for the given address.

        If there is no previous nonce record for the address, the nonce may be initialized to a specified value, or 0 if no value has been given.

        :param address: Associate Ethereum address 
        :type address: str, 0x-hex
        :param initial_if_not_exists: Initial nonce value to set if no record exists
        :type initial_if_not_exists: number
        :returns: Nonce
        :rtype: number
        """
        session = SessionBase.bind_session(session)
        
        SessionBase.release_session(session)

        session.begin_nested()
        #conn = Nonce.engine.connect()
        if Nonce.transactional:
            #session.execute('BEGIN')
            session.execute('LOCK TABLE nonce IN SHARE ROW EXCLUSIVE MODE')
            session.flush()
        nonce = Nonce.__get(session, address)
        logg.debug('get nonce {} for address {}'.format(nonce, address))
        if nonce == None:
            nonce = initial_if_not_exists
            session.execute("INSERT INTO nonce (nonce, address_hex) VALUES ({}, '{}')".format(nonce, address))
            session.flush()
            logg.debug('setting default nonce to {} for address {}'.format(nonce, address))
        Nonce.__set(session, address, nonce+1)
        #if Nonce.transactional:
            #session.execute('COMMIT')
            #session.execute('UNLOCK TABLE nonce')
        #conn.close()
        session.commit()
        session.commit()

        SessionBase.release_session(session)
        return nonce


