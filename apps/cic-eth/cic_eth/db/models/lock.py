# standard imports
import datetime
import logging

# third-party imports
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from chainlib.eth.constant import ZERO_ADDRESS

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.otx import Otx

logg = logging.getLogger()


class Lock(SessionBase):
    """Deactivate functionality on a global or per-account basis

    """

    __tablename__ = "lock"

    blockchain = Column(String)
    address = Column(String, ForeignKey('tx_cache.sender'))
    flags = Column(Integer)
    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    otx_id = Column(Integer, ForeignKey('otx.id'))


    def chain(self):
        """Get chain the cached instance represents.
        """
        return self.blockchain


    @staticmethod
    def set(chain_str, flags, address=ZERO_ADDRESS, session=None, tx_hash=None):
        """Sets flags associated with the given address and chain.

        If a flags entry does not exist it is created.

        Does not validate the address against any other tables or components.

        Valid flags can be found in cic_eth.db.enum.LockEnum.

        :param chain_str: Chain spec string representation
        :type str: str
        :param flags: Flags to set
        :type flags: number
        :param address: Ethereum address
        :type address: str, 0x-hex
        :param session: Database session, if None a separate session will be used.
        :type session: SQLAlchemy session
        :returns: New flag state of entry
        :rtype: number
        """
        session = SessionBase.bind_session(session)

        q = session.query(Lock)
        #q = q.join(TxCache, isouter=True)
        q = q.filter(Lock.address==address)
        q = q.filter(Lock.blockchain==chain_str)
        lock = q.first()
        
        if lock == None:
            lock = Lock()
            lock.flags = 0
            lock.address = address
            lock.blockchain = chain_str
            if tx_hash != None:
                session.flush()
                q = session.query(Otx)
                q = q.filter(Otx.tx_hash==tx_hash)
                otx = q.first()
                if otx != None:
                    lock.otx_id = otx.id

        lock.flags |= flags
        r = lock.flags

        session.add(lock)
        session.commit()

        SessionBase.release_session(session)

        return r


    @staticmethod
    def reset(chain_str, flags, address=ZERO_ADDRESS, session=None):
        """Resets flags associated with the given address and chain.

        If the resulting flags entry value is 0, the entry will be deleted.

        Does not validate the address against any other tables or components.

        Valid flags can be found in cic_eth.db.enum.LockEnum.

        :param chain_str: Chain spec string representation
        :type str: str
        :param flags: Flags to set
        :type flags: number
        :param address: Ethereum address
        :type address: str, 0x-hex
        :param session: Database session, if None a separate session will be used.
        :type session: SQLAlchemy session
        :returns: New flag state of entry
        :rtype: number
        """
        session = SessionBase.bind_session(session)

        q = session.query(Lock)
        #q = q.join(TxCache, isouter=True)
        q = q.filter(Lock.address==address)
        q = q.filter(Lock.blockchain==chain_str)
        lock = q.first()

        r = 0
        if lock != None:
            lock.flags &= ~flags
            if lock.flags == 0:
                session.delete(lock)
            else:
                session.add(lock)
                r = lock.flags
            session.commit()

        SessionBase.release_session(session)

        return r


    @staticmethod
    def check(chain_str, flags, address=ZERO_ADDRESS, session=None):
        """Checks whether all given flags are set for given address and chain. 

        Does not validate the address against any other tables or components.

        Valid flags can be found in cic_eth.db.enum.LockEnum.

        :param chain_str: Chain spec string representation
        :type str: str
        :param flags: Flags to set
        :type flags: number
        :param address: Ethereum address
        :type address: str, 0x-hex
        :param session: Database session, if None a separate session will be used.
        :type session: SQLAlchemy session
        :returns: Returns the value of all flags matched
        :rtype: number
        """

        session = SessionBase.bind_session(session)

        q = session.query(Lock)
        #q = q.join(TxCache, isouter=True)
        q = q.filter(Lock.address==address)
        q = q.filter(Lock.blockchain==chain_str)
        q = q.filter(Lock.flags.op('&')(flags)==flags)
        lock = q.first()
       
        r = 0
        if lock != None:
            r = lock.flags & flags

        SessionBase.release_session(session)
        return r


    @staticmethod
    def check_aggregate(chain_str, flags, address, session=None):
        localsession = session
        if localsession == None:
            localsession = SessionBase.create_session()

        r = Lock.check(chain_str, flags, session=localsession) 
        r |= Lock.check(chain_str, flags, address=address, session=localsession) 

        if session == None:
            localsession.close()

        return r
