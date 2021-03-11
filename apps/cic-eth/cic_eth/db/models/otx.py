# standard imports
import datetime
import logging

# external imports
from sqlalchemy import Column, Enum, String, Integer, DateTime, Text, or_, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

# local imports
from .base import SessionBase
from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        status_str,
        is_error_status,
        )
from cic_eth.db.error import TxStateChangeError
#from cic_eth.eth.util import address_hex_from_signed_tx

logg = logging.getLogger()


class OtxStateLog(SessionBase):

    __tablename__ = 'otx_state_log'

    date = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(Integer)
    otx_id = Column(Integer, ForeignKey('otx.id'))


    def __init__(self, otx):
        self.otx_id = otx.id
        self.status = otx.status


class Otx(SessionBase):
    """Outgoing transactions with local origin.

    :param nonce: Transaction nonce
    :type nonce: number
    :param address: Ethereum address of recipient - NOT IN USE, REMOVE
    :type address: str
    :param tx_hash: Tranasction hash 
    :type tx_hash: str, 0x-hex
    :param signed_tx: Signed raw transaction data
    :type signed_tx: str, 0x-hex
    """
    __tablename__ = 'otx'

    tracing = False
    """Whether to enable queue state tracing"""

    nonce = Column(Integer)
    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    tx_hash = Column(String(66))
    signed_tx = Column(Text)
    status = Column(Integer)
    block = Column(Integer)


    def __set_status(self, status, session):
        self.status |= status
        session.add(self)
        session.flush()


    def __reset_status(self, status, session):
        status_edit = ~status & self.status
        self.status &= status_edit
        session.add(self)
        session.flush()
   

    def __status_already_set(self, status):
        r = bool(self.status & status)
        if r:
            logg.warning('status bit {} already set on {}'.format(status.name, self.tx_hash))
        return r


    def __status_not_set(self, status):
        r = not(self.status & status)
        if r:
            logg.warning('status bit {} not set on {}'.format(status.name, self.tx_hash))
        return r


    def set_block(self, block, session=None):
        """Set block number transaction was mined in.

        Only manipulates object, does not transaction or commit to backend.

        :param block: Block number
        :type block: number
        :raises cic_eth.db.error.TxStateChangeError: State change represents a sequence of events that should not exist.
        """
        session = SessionBase.bind_session(session)

        if self.block != None:
            SessionBase.release_session(session)
            raise TxStateChangeError('Attempted set block {} when block was already {}'.format(block, self.block))
        self.block = block
        session.add(self)
        session.flush()

        SessionBase.release_session(session)


    def waitforgas(self, session=None):
        """Marks transaction as suspended pending gas funding.

        Only manipulates object, does not transaction or commit to backend.

        :raises cic_eth.db.error.TxStateChangeError: State change represents a sequence of events that should not exist.
        """
        if self.__status_already_set(StatusBits.GAS_ISSUES):
            return

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('GAS_ISSUES cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))
        if self.status & StatusBits.IN_NETWORK:
            SessionBase.release_session(session)
            raise TxStateChangeError('GAS_ISSUES cannot be set on an entry with IN_NETWORK state set ({})'.format(status_str(self.status)))

        self.__set_status(StatusBits.GAS_ISSUES, session)
        self.__reset_status(StatusBits.QUEUED | StatusBits.DEFERRED, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    def fubar(self, session=None):
        """Marks transaction as "fubar." Any transaction marked this way is an anomaly and may be a symptom of a serious problem.

        Only manipulates object, does not transaction or commit to backend.
        """
        if self.__status_already_set(StatusBits.UNKNOWN_ERROR):
            return

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('FUBAR cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))
        if is_error_status(self.status):
            SessionBase.release_session(session)
            raise TxStateChangeError('FUBAR cannot be set on an entry with an error state already set ({})'.format(status_str(self.status)))

        self.__set_status(StatusBits.UNKNOWN_ERROR | StatusBits.FINAL, session)
       
        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    def reject(self, session=None):
        """Marks transaction as "rejected," which means the node rejected sending the transaction to the network. The nonce has not been spent, and the transaction should be replaced.

        Only manipulates object, does not transaction or commit to backend.
        """
        if self.__status_already_set(StatusBits.NODE_ERROR):
            return

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('REJECTED cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))
        if self.status & StatusBits.IN_NETWORK:
            SessionBase.release_session(session)
            raise TxStateChangeError('REJECTED cannot be set on an entry already IN_NETWORK ({})'.format(status_str(self.status)))
        if is_error_status(self.status):
            SessionBase.release_session(session)
            raise TxStateChangeError('REJECTED cannot be set on an entry with an error state already set ({})'.format(status_str(self.status)))

        self.__set_status(StatusBits.NODE_ERROR | StatusBits.FINAL, session)
            
        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    def override(self, manual=False, session=None):
        """Marks transaction as manually overridden.

        Only manipulates object, does not transaction or commit to backend.
        """

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('OVERRIDDEN/OBSOLETED cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))
        if self.status & StatusBits.IN_NETWORK:
            SessionBase.release_session(session)
            raise TxStateChangeError('OVERRIDDEN/OBSOLETED cannot be set on an entry already IN_NETWORK ({})'.format(status_str(self.status)))
        if self.status & StatusBits.OBSOLETE:
            SessionBase.release_session(session)
            raise TxStateChangeError('OVERRIDDEN/OBSOLETED cannot be set on an entry already OBSOLETE ({})'.format(status_str(self.status)))

        self.__set_status(StatusBits.OBSOLETE, session)
        #if manual:
        #    self.__set_status(StatusBits.MANUAL, session)
        self.__reset_status(StatusBits.QUEUED | StatusBits.IN_NETWORK, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    def manual(self, session=None):

        session = SessionBase.bind_session(session)


        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('OVERRIDDEN/OBSOLETED cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))

        self.__set_status(StatusBits.MANUAL, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)

    def retry(self, session=None):
        """Marks transaction as ready to retry after a timeout following a sendfail or a completed gas funding.

        Only manipulates object, does not transaction or commit to backend.

        :raises cic_eth.db.error.TxStateChangeError: State change represents a sequence of events that should not exist.
        """
        if self.__status_already_set(StatusBits.QUEUED):
            return

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('RETRY cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))
        if not is_error_status(self.status) and not StatusBits.IN_NETWORK & self.status > 0:
            SessionBase.release_session(session)
            raise TxStateChangeError('RETRY cannot be set on an entry that has no error ({})'.format(status_str(self.status)))

        self.__set_status(StatusBits.QUEUED, session)
        self.__reset_status(StatusBits.GAS_ISSUES, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    def readysend(self, session=None):
        """Marks transaction as ready for initial send attempt.

        Only manipulates object, does not transaction or commit to backend.

        :raises cic_eth.db.error.TxStateChangeError: State change represents a sequence of events that should not exist.
        """
        if self.__status_already_set(StatusBits.QUEUED):
            return

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('READYSEND cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))
        if is_error_status(self.status):
            SessionBase.release_session(session)
            raise TxStateChangeError('READYSEND cannot be set on an errored state ({})'.format(status_str(self.status)))

        self.__set_status(StatusBits.QUEUED, session)
        self.__reset_status(StatusBits.GAS_ISSUES, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    def sent(self, session=None):
        """Marks transaction as having been sent to network.

        Only manipulates object, does not transaction or commit to backend.

        :raises cic_eth.db.error.TxStateChangeError: State change represents a sequence of events that should not exist.
        """
        if self.__status_already_set(StatusBits.IN_NETWORK):
            return

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('SENT cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))

        self.__set_status(StatusBits.IN_NETWORK, session)
        self.__reset_status(StatusBits.DEFERRED | StatusBits.QUEUED | StatusBits.LOCAL_ERROR | StatusBits.NODE_ERROR, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    def sendfail(self, session=None):
        """Marks that an attempt to send the transaction to the network has failed.

        Only manipulates object, does not transaction or commit to backend.

        :raises cic_eth.db.error.TxStateChangeError: State change represents a sequence of events that should not exist.
        """
        if self.__status_already_set(StatusBits.NODE_ERROR):
            return

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('SENDFAIL cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))
        if self.status & StatusBits.IN_NETWORK:
            SessionBase.release_session(session)
            raise TxStateChangeError('SENDFAIL cannot be set on an entry with IN_NETWORK state set ({})'.format(status_str(self.status)))

        self.__set_status(StatusBits.LOCAL_ERROR | StatusBits.DEFERRED, session)
        self.__reset_status(StatusBits.QUEUED | StatusBits.GAS_ISSUES, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    def dequeue(self, session=None):
        """Marks that a process to execute send attempt is underway

        Only manipulates object, does not transaction or commit to backend.

        :raises cic_eth.db.error.TxStateChangeError: State change represents a sequence of events that should not exist.
        """
        if self.__status_not_set(StatusBits.QUEUED):
            return

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('SENDFAIL cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))
        if self.status & StatusBits.IN_NETWORK:
            SessionBase.release_session(session)
            raise TxStateChangeError('SENDFAIL cannot be set on an entry with IN_NETWORK state set ({})'.format(status_str(self.status)))

        self.__reset_status(StatusBits.QUEUED, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)



    def minefail(self, block, session=None):
        """Marks that transaction was mined but code execution did not succeed.

        Only manipulates object, does not transaction or commit to backend.

        :param block: Block number transaction was mined in.
        :type block: number
        :raises cic_eth.db.error.TxStateChangeError: State change represents a sequence of events that should not exist.
        """
        if self.__status_already_set(StatusBits.NETWORK_ERROR):
            return

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('REVERTED cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))
        if not self.status & StatusBits.IN_NETWORK:
            SessionBase.release_session(session)
            raise TxStateChangeError('REVERTED cannot be set on an entry without IN_NETWORK state set ({})'.format(status_str(self.status)))

        if block != None:
            self.block = block

        self.__set_status(StatusBits.NETWORK_ERROR | StatusBits.FINAL, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    def cancel(self, confirmed=False, session=None):
        """Marks that the transaction has been succeeded by a new transaction with same nonce.

        If set to confirmed, the previous state must be OBSOLETED, and will transition to CANCELLED - a finalized state. Otherwise, the state must follow a non-finalized state, and will be set to OBSOLETED.

        Only manipulates object, does not transaction or commit to backend.

        :param confirmed: Whether transition is to a final state.
        :type confirmed: bool
        :raises cic_eth.db.error.TxStateChangeError: State change represents a sequence of events that should not exist.
        """
        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('CANCEL cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))

        if confirmed:
            if self.status > 0 and not self.status & StatusBits.OBSOLETE:
                SessionBase.release_session(session)
                raise TxStateChangeError('CANCEL can only be set on an entry marked OBSOLETE ({})'.format(status_str(self.status)))
            self.__set_status(StatusEnum.CANCELLED, session)
        else:
            self.__set_status(StatusEnum.OBSOLETED, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    def success(self, block, session=None):
        """Marks that transaction was successfully mined.

        Only manipulates object, does not transaction or commit to backend.

        :param block: Block number transaction was mined in.
        :type block: number
        :raises cic_eth.db.error.TxStateChangeError: State change represents a sequence of events that should not exist.
        """

        session = SessionBase.bind_session(session)

        if self.status & StatusBits.FINAL:
            SessionBase.release_session(session)
            raise TxStateChangeError('SUCCESS cannot be set on an entry with FINAL state set ({})'.format(status_str(self.status)))
        if not self.status & StatusBits.IN_NETWORK:
            SessionBase.release_session(session)
            raise TxStateChangeError('SUCCESS cannot be set on an entry without IN_NETWORK state set ({})'.format(status_str(self.status)))
        if is_error_status(self.status):
            SessionBase.release_session(session)
            raise TxStateChangeError('SUCCESS cannot be set on an entry with error state set ({})'.format(status_str(self.status)))

        if block != None:
            self.block = block
        self.__set_status(StatusEnum.SUCCESS, session)

        if self.tracing:
            self.__state_log(session=session)

        SessionBase.release_session(session)


    @staticmethod
    def get(status=0, limit=4096, status_exact=True, session=None):
        """Returns outgoing transaction lists by status.

        Status may either be matched exactly, or be an upper bound of the integer value of the status enum.

        :param status: Status value to use in query
        :type status: cic_eth.db.enum.StatusEnum
        :param limit: Max results to return
        :type limit: number
        :param status_exact: Whether or not to perform exact status match
        :type bool:
        :returns: List of transaction hashes
        :rtype: tuple, where first element is transaction hash
        """
        e = None

        session = SessionBase.bind_session(session)

        if status_exact:
            e = session.query(Otx.tx_hash).filter(Otx.status==status).order_by(Otx.date_created.asc()).limit(limit).all()
        else:
            e = session.query(Otx.tx_hash).filter(Otx.status<=status).order_by(Otx.date_created.asc()).limit(limit).all()
        
        SessionBase.release_session(session)
        return e


    @staticmethod
    def load(tx_hash, session=None):
        """Retrieves the outgoing transaction record by transaction hash.

        :param tx_hash: Transaction hash
        :type tx_hash: str, 0x-hex
        """
        session = SessionBase.bind_session(session)
        
        q = session.query(Otx)
        q = q.filter(Otx.tx_hash==tx_hash)

        SessionBase.release_session(session)

        return q.first()


    @staticmethod
    def account(account_address):
        """Retrieves all transaction hashes for which the given Ethereum address is sender or recipient.

        :param account_address: Ethereum address to use in query.
        :type account_address: str, 0x-hex
        :returns: Outgoing transactions
        :rtype: tuple, where first element is transaction hash
        """
        session = Otx.create_session()
        q = session.query(Otx.tx_hash)
        q = q.join(TxCache)
        q = q.filter(or_(TxCache.sender==account_address, TxCache.recipient==account_address))
        txs = q.all()
        session.close()
        return list(txs)


    def __state_log(self, session):
        l = OtxStateLog(self)
        session.add(l)


    # TODO: it is not safe to return otx here unless session has been passed in
    @staticmethod
    def add(nonce, address, tx_hash, signed_tx, session=None):
        external_session = session != None

        session = SessionBase.bind_session(session)

        otx = Otx(nonce, address, tx_hash, signed_tx)
        session.add(otx)
        session.flush()
        if otx.tracing:
            otx.__state_log(session=session)
        session.flush()

        SessionBase.release_session(session)
        
        if not external_session:
            return None

        return otx


    def __init__(self, nonce, address, tx_hash, signed_tx):
        self.nonce = nonce
        self.tx_hash = tx_hash
        self.signed_tx = signed_tx
        self.status = StatusEnum.PENDING
        signed_tx_bytes = bytes.fromhex(signed_tx[2:])

       # sender_address = address_hex_from_signed_tx(signed_tx_bytes)
       # logg.debug('decoded tx {}'.format(sender_address))

    

# TODO: Most of the methods on this object are obsolete, but it contains a static function for retrieving "expired" outgoing transactions that should be moved to Otx instead.
class OtxSync(SessionBase):
    """Obsolete
    """
    __tablename__ = 'otx_sync'

    blockchain = Column(String)
    block_height_backlog = Column(Integer)
    tx_height_backlog = Column(Integer)
    block_height_session = Column(Integer)
    tx_height_session = Column(Integer)
    block_height_head = Column(Integer)
    tx_height_head = Column(Integer)
    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    date_updated = Column(DateTime)


    def backlog(self, block_height=None, tx_height=None):
        #session = OtxSync.create_session()
        if block_height != None:
            if tx_height == None:
                raise ValueError('tx height missing')
            self.block_height_backlog = block_height
            self.tx_height_backlog = tx_height
            #session.add(self)
            self.date_updated = datetime.datetime.utcnow()
        #session.commit()
        block_height = self.block_height_backlog
        tx_height = self.tx_height_backlog
        #session.close()
        return (block_height, tx_height)
   

    def session(self, block_height=None, tx_height=None):
        #session = OtxSync.create_session()
        if block_height != None:
            if tx_height == None:
                raise ValueError('tx height missing')
            self.block_height_session = block_height
            self.tx_height_session = tx_height
            #session.add(self)
            self.date_updated = datetime.datetime.utcnow()
        #session.commit()
        block_height = self.block_height_session
        tx_height = self.tx_height_session
        #session.close()
        return (block_height, tx_height)


    def head(self, block_height=None, tx_height=None):
        #session = OtxSync.create_session()
        if block_height != None:
            if tx_height == None:
                raise ValueError('tx height missing')
            self.block_height_head = block_height
            self.tx_height_head = tx_height
            #session.add(self)
            self.date_updated = datetime.datetime.utcnow()
        #session.commit()
        block_height = self.block_height_head
        tx_height = self.tx_height_head
        #session.close()
        return (block_height, tx_height)


    @hybrid_property
    def synced(self):
        #return self.block_height_session == self.block_height_backlog and self.tx_height_session == self.block_height_backlog
        return self.block_height_session == self.block_height_backlog and self.tx_height_session == self.tx_height_backlog


    @staticmethod
    def load(blockchain_string, session):
        q = session.query(OtxSync)
        q = q.filter(OtxSync.blockchain==blockchain_string)
        return q.first()


    @staticmethod
    def latest(nonce):
        session = SessionBase.create_session()
        otx = session.query(Otx).filter(Otx.nonce==nonce).order_by(Otx.created.desc()).first()
        session.close()
        return otx


    @staticmethod
    def get_expired(datetime_threshold):
        session = SessionBase.create_session()
        q = session.query(Otx)
        q = q.filter(Otx.date_created<datetime_threshold)
        q = q.filter(Otx.status==StatusEnum.SENT)
        q = q.order_by(Otx.date_created.desc())
        q = q.group_by(Otx.nonce)
        q = q.group_by(Otx.id)
        otxs = q.all()
        session.close()
        return otxs


    def chain(self):
        return self.blockchain


    def __init__(self, blockchain):
        self.blockchain = blockchain
        self.block_height_head = 0
        self.tx_height_head = 0
        self.block_height_session = 0
        self.tx_height_session = 0
        self.block_height_backlog = 0
        self.tx_height_backlog = 0
