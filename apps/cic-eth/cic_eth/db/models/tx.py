# standard imports
import datetime

# third-party imports
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, Boolean, NUMERIC
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
#from sqlalchemy.orm import relationship, backref
#from sqlalchemy.ext.declarative import declarative_base

# local imports
from .base import SessionBase
from .otx import Otx
from cic_eth.db.util import num_serialize
from cic_eth.error import NotLocalTxError
from cic_eth.db.error import TxStateChangeError


class TxCache(SessionBase):
    """Metadata expansions for outgoing transactions.

    These records are not essential for handling of outgoing transaction queues. It is implemented to reduce the amount of computation spent of parsing and analysing raw signed transaction data.

    Instantiation of the object will fail if an outgoing transaction record with the same transaction hash does not exist.

    Typically three types of transactions are recorded:

    - Token transfers; where source and destination token values and addresses are identical, sender and recipient differ.
    - Token conversions; source and destination token values and addresses differ, sender and recipient are identical.
    - Any other transaction; source and destination token addresses are zero-address.

    :param tx_hash: Transaction hash
    :type tx_hash: str, 0x-hex
    :param sender: Ethereum address of transaction sender
    :type sender: str, 0x-hex
    :param recipient: Ethereum address of transaction beneficiary (e.g. token transfer recipient)
    :type recipient: str, 0x-hex
    :param source_token_address: Contract address of token that sender spent from
    :type source_token_address: str, 0x-hex
    :param destination_token_address: Contract address of token that recipient will receive balance of
    :type destination_token_address: str, 0x-hex
    :param from_value: Amount of source tokens spent
    :type from_value: number
    :param to_value: Amount of destination tokens received
    :type to_value: number
    :param block_number: Block height the transaction was mined at, or None if not yet mined
    :type block_number: number or None
    :param tx_number: Block transaction height the transaction was mined at, or None if not yet mined
    :type tx_number: number or None
    :raises FileNotFoundError: Outgoing transaction for given transaction hash does not exist
    """
    __tablename__ = 'tx_cache'

    otx_id = Column(Integer, ForeignKey('otx.id'))
    source_token_address = Column(String(42))
    destination_token_address = Column(String(42))
    sender = Column(String(42))
    recipient = Column(String(42))
    from_value = Column(NUMERIC())
    to_value = Column(NUMERIC())
    block_number = Column(Integer())
    tx_index = Column(Integer())
    date_created = Column(DateTime, default=datetime.datetime.utcnow)
    date_updated = Column(DateTime, default=datetime.datetime.utcnow)
    date_checked = Column(DateTime, default=datetime.datetime.utcnow)


    def check(self):
        """Update the "checked" timestamp to current time.

        Only manipulates object, does not transaction or commit to backend.
        """
        self.date_checked = datetime.datetime.now()


    @staticmethod
    def clone(
            tx_hash_original,
            tx_hash_new,
            session=None,
            ):
        """Copy tx cache data and associate it with a new transaction.

        :param tx_hash_original: tx cache data to copy
        :type tx_hash_original: str, 0x-hex
        :param tx_hash_new: tx hash to associate the copied entry with
        :type tx_hash_new: str, 0x-hex
        """
        session = SessionBase.bind_session(session)
        
        q = session.query(TxCache)
        q = q.join(Otx)
        q = q.filter(Otx.tx_hash==tx_hash_original)
        txc = q.first()

        if txc == None:
            SessionBase.release_session(session)
            raise NotLocalTxError('original {}'.format(tx_hash_original))
        if txc.block_number != None:
            SessionBase.release_session(session)
            raise TxStateChangeError('cannot clone tx cache of confirmed tx {}'.format(tx_hash_original))

        session.flush()
        q = session.query(Otx)
        q = q.filter(Otx.tx_hash==tx_hash_new)
        otx = q.first()

        if otx == None:
            SessionBase.release_session(session)
            raise NotLocalTxError('new {}'.format(tx_hash_new))

        txc_new = TxCache(
                otx.tx_hash,
                txc.sender,
                txc.recipient,
                txc.source_token_address,
                txc.destination_token_address,
                int(txc.from_value),
                int(txc.to_value),
                session=session,
                )
        session.add(txc_new)
        session.commit()

        SessionBase.release_session(session)


    def __init__(self, tx_hash, sender, recipient, source_token_address, destination_token_address, from_value, to_value, block_number=None, tx_index=None, session=None):
        session = SessionBase.bind_session(session)
        q = session.query(Otx)
        q = q.filter(Otx.tx_hash==tx_hash)
        tx = q.first()
        if tx == None:
            SessionBase.release_session(session)
            raise FileNotFoundError('outgoing transaction record unknown {} (add a Tx first)'.format(tx_hash))
        self.otx_id = tx.id

        self.sender = sender
        self.recipient = recipient
        self.source_token_address = source_token_address
        self.destination_token_address = destination_token_address
        self.from_value = from_value
        self.to_value = to_value
        self.block_number = block_number
        self.tx_index = tx_index
        # not automatically set in sqlite, it seems:
        self.date_created = datetime.datetime.utcnow()
        self.date_updated = self.date_created
        self.date_checked = self.date_created

        SessionBase.release_session(session)

