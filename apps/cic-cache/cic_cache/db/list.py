# standard imports
import logging
import datetime

# external imports
from cic_cache.db.models.base import SessionBase
from sqlalchemy import text

logg = logging.getLogger()


def list_transactions_mined(
        session,
        offset,
        limit,
        ):
    """Executes db query to return all confirmed transactions according to the specified offset and limit.

    :param offset: Offset in data set to return transactions from
    :type offset: int
    :param limit: Max number of transactions to retrieve
    :type limit: int
    :result: Result set
    :rtype: SQLAlchemy.ResultProxy
    """
    s = "SELECT block_number, tx_index FROM tx ORDER BY block_number DESC, tx_index DESC LIMIT {} OFFSET {}".format(limit, offset)
    r = session.execute(s)
    return r


def list_transactions_account_mined(
        session,
        address,
        offset,
        limit,
        ):
    """Same as list_transactions_mined(...), but only retrieves transaction where the specified account address is sender or recipient.

    :param address: Address to retrieve transactions for.
    :type address: str, 0x-hex
    :param offset: Offset in data set to return transactions from
    :type offset: int
    :param limit: Max number of transactions to retrieve
    :type limit: int
    :result: Result set
    :rtype: SQLAlchemy.ResultProxy
    """
    s = "SELECT block_number, tx_index FROM tx WHERE sender = '{}' OR recipient = '{}' ORDER BY block_number DESC, tx_index DESC LIMIT {} OFFSET {}".format(address, address, limit, offset)
    r = session.execute(s)
    return r


def add_transaction(
        session,
        tx_hash,
        block_number,
        tx_index,
        sender,
        receiver,
        source_token,
        destination_token,
        from_value,
        to_value,
        success,
        timestamp,
        ):
    """Adds a single transaction to the cache persistent storage. Sensible interpretation of all fields is the responsibility of the caller.

    :param session: Persistent storage session object
    :type session: SQLAlchemy session
    :param tx_hash: Transaction hash
    :type tx_hash: str, 0x-hex
    :param block_number: Block number
    :type block_number: int
    :param tx_index: Transaction index in block
    :type tx_index: int
    :param sender: Ethereum address of effective sender
    :type sender: str, 0x-hex
    :param receiver: Ethereum address of effective recipient
    :type receiver: str, 0x-hex
    :param source_token: Ethereum address of token used by sender
    :type source_token: str, 0x-hex
    :param destination_token: Ethereum address of token received by recipient
    :type destination_token: str, 0x-hex
    :param from_value: Source token value spent in transaction
    :type from_value: int
    :param to_value: Destination token value received in transaction
    :type to_value: int
    :param success: True if code execution on network was successful
    :type success: bool
    :param date_block: Block timestamp
    :type date_block: datetime
    """
    date_block = datetime.datetime.fromtimestamp(timestamp)
    s = "INSERT INTO tx (tx_hash, block_number, tx_index, sender, recipient, source_token, destination_token, from_value, to_value, success, date_block) VALUES ('{}', {}, {}, '{}', '{}', '{}', '{}', {}, {}, {}, '{}')".format(
            tx_hash,
            block_number,
            tx_index,
            sender,
            receiver,
            source_token,
            destination_token,
            from_value,
            to_value,
            success,
            date_block,
            )
    session.execute(s)



def tag_transaction(
        session,
        tx_hash,
        name,
        domain=None,
        ):
    """Tag a single transaction with a single tag.

    Tag must already exist in storage.

    :param session: Persistent storage session object
    :type session: SQLAlchemy session
    :param tx_hash: Transaction hash
    :type tx_hash: str, 0x-hex
    :param name: Tag value
    :type name: str
    :param domain: Tag domain
    :type domain: str
    :raises ValueError: Unknown tag or transaction hash

    """

    s = text("SELECT id from tx where tx_hash = :a")
    r = session.execute(s, {'a': tx_hash}).fetchall()
    tx_id = r[0].values()[0]

    if tx_id == None:
        raise ValueError('unknown tx hash {}'.format(tx_hash))

    #s = text("SELECT id from tag where value = :a and domain = :b")
    if domain == None:
        s = text("SELECT id from tag where value = :a")
    else:
        s = text("SELECT id from tag where value = :a and domain = :b")
    r = session.execute(s, {'a': name, 'b': domain}).fetchall()
    tag_id = r[0].values()[0]

    logg.debug('type {} {}'.format(type(tag_id), type(tx_id)))

    if tag_id == None:
        raise ValueError('unknown tag name {} domain {}'.format(name, domain))

    s = text("INSERT INTO tag_tx_link (tag_id, tx_id) VALUES (:a, :b)")
    r = session.execute(s, {'a': int(tag_id), 'b': int(tx_id)})


def add_tag(
        session,
        name,
        domain=None,
        ):
    """Add a single tag to storage.

    :param session: Persistent storage session object
    :type session: SQLAlchemy session
    :param name: Tag value
    :type name: str
    :param domain: Tag domain
    :type domain: str
    :raises sqlalchemy.exc.IntegrityError: Tag already exists
    """

    s = None
    if domain == None: 
        s = text("INSERT INTO tag (value) VALUES (:b)")
    else:
        s = text("INSERT INTO tag (domain, value) VALUES (:a, :b)")
    session.execute(s, {'a': domain, 'b': name})
