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
        block_offset,
        block_limit,
        oldest=False,
        ):
    """Executes db query to return all confirmed transactions according to the specified offset and limit.

    :param offset: Offset in data set to return transactions from
    :type offset: int
    :param limit: Max number of transactions to retrieve
    :type limit: int
    :result: Result set
    :rtype: SQLAlchemy.ResultProxy
    """
    order_by = 'DESC'
    if oldest:
        order_by = 'ASC'

    if block_offset:
        if block_limit:
            s = "SELECT block_number, tx_index FROM tx ORDER BY block_number {}, tx_index {} WHERE block_number >= {} and block_number <= {} LIMIT {} OFFSET {}".format(order_by, order_by, limit, offset, block_offset, block_limit)
        else:
            s = "SELECT block_number, tx_index FROM tx ORDER BY block_number {}, tx_index {} WHERE block_number >= {} LIMIT {} OFFSET {}".format(order_by, order_by, limit, offset, block_offset)
    else:
        s = "SELECT block_number, tx_index FROM tx ORDER BY block_number {}, tx_index {} LIMIT {} OFFSET {}".format(order_by, order_by, limit, offset)
    r = session.execute(s)
    return r


def list_transactions_mined_with_data(
        session,
        offset,
        limit,
        block_offset,
        block_limit,
        oldest=False,
        ):
    """Executes db query to return all confirmed transactions according to the specified offset and limit.

    :param block_offset: First block to include in search
    :type block_offset: int
    :param block_limit: Last block to include in search
    :type block_limit: int
    :result: Result set
    :rtype: SQLAlchemy.ResultProxy
    """
    order_by = 'DESC'
    if oldest:
        order_by = 'ASC'

    if block_offset:
        if block_limit:
            s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id WHERE block_number >= {} AND block_number <= {} ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(block_offset, block_limit, order_by, order_by, offset, limit)
        else:
            s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id WHERE block_number >= {} ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(block_offset, order_by, order_by, offset, limit)
    else:
        s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(order_by, order_by, offset, limit)


    r = session.execute(s)
    return r


def list_transactions_mined_with_data_index(
        session,
        offset,
        end,
        block_offset,
        block_limit,
        oldest=False,
        ):
    """Executes db query to return all confirmed transactions according to the specified offset and limit.

    :param offset: Offset in data set to return transactions from
    :type offset: int
    :param limit: Max number of transactions to retrieve
    :type limit: int
    :result: Result set
    :rtype: SQLAlchemy.ResultProxy
    """

    order_by = 'DESC'
    if oldest:
        order_by = 'ASC'

    if block_offset:
        if block_limit:
            s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id WHERE block_number >= {} and block_number <= {} ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(block_offset, block_limit, order_by, order_by, offset, end)
        else:
            s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id WHERE block_number >= {} ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(block_offset, order_by, order_by, offset, end)
    else:
        s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(order_by, order_by, offset, end)

    r = session.execute(s)
    return r


def list_transactions_account_mined_with_data_index(
        session,
        address,
        offset,
        limit,
        block_offset,
        block_limit,
        oldest=False,
        ):
    """Executes db query to return all confirmed transactions according to the specified offset and limit, filtered by address

    :param offset: Offset in data set to return transactions from
    :type offset: int
    :param limit: Max number of transactions to retrieve
    :type limit: int
    :result: Result set
    :rtype: SQLAlchemy.ResultProxy
    """

    order_by = 'DESC'
    if oldest:
        order_by = 'ASC'

    if block_offset:
        if block_limit:
            s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id WHERE block_number >= {} AND block_number <= {} AND (sender = '{}' OR recipient = '{}') ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(block_offset, block_limit, address, address, order_by, order_by, offset, limit)
        else:
            s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id WHERE block_number >= {} AND (sender = '{}' OR recipient = '{}') ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(block_offset, address, address, order_by, order_by, offset, limit)
    else:
        s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id WHERE sender = '{}' OR recipient = '{}' ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(address, address, order_by, order_by, offset, limit)

    r = session.execute(s)
    return r

def list_transactions_account_mined_with_data(
        session,
        address,
        offset,
        limit,
        block_offset,
        block_limit,
        oldest=False,
        ):
    """Executes db query to return all confirmed transactions according to the specified offset and limit.

    :param block_offset: First block to include in search
    :type block_offset: int
    :param block_limit: Last block to include in search
    :type block_limit: int
    :result: Result set
    :rtype: SQLAlchemy.ResultProxy
    """

    order_by = 'DESC'
    if oldest:
        order_by = 'ASC'

    if block_offset:
        if block_limit:
            s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id WHERE block_number >= {} AND block_number <= {} AND (sender = '{}' OR recipient = '{}') ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(block_offset, block_limit, address, address, order_by, order_by, offset, limit)
        else:
            s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id WHERE block_number >= {} AND (sender = '{}' OR recipient = '{}') ORDER BY block_number {}, tx_index {} OFFSET {} LIMIT {}".format(block_offset, address, address, order_by, order_by, offset, limit)
    else:
        s = "SELECT tx_hash, block_number, date_block, sender, recipient, from_value, to_value, source_token, destination_token, success, domain, value FROM tx LEFT JOIN tag_tx_link ON tx.id = tag_tx_link.tx_id LEFT JOIN tag ON tag_tx_link.tag_id = tag.id WHERE sender = '{}' OR recipient = '{}' ORDER BY block_number , tx_index {} OFFSET {} LIMIT {}".format(address, address, order_by, order_by, offset, limit)

    r = session.execute(s)
    return r


def list_transactions_account_mined(
        session,
        address,
        offset,
        limit,
        block_offset,
        block_limit,
        oldest=False,
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

    order_by = 'DESC'
    if oldest:
        order_by = 'ASC'

    if block_offset:
        if block_limit:
            s = "SELECT block_number, tx_index FROM tx WHERE block_number >= {} AND block_number <= {} AND (sender = '{}' OR recipient = '{}') ORDER BY block_number {}, tx_index {} LIMIT {} OFFSET {}".format(block_offset, block_limit, address, address, order_by, order_by, limit, offset)
        else:
            s = "SELECT block_number, tx_index FROM tx WHERE block_number >= {} AND (sender = '{}' OR recipient = '{}') ORDER BY block_number {}, tx_index {} LIMIT {} OFFSET {}".format(block_offset, address, address, order_by, order_by, limit, offset)

    else:
        s = "SELECT block_number, tx_index FROM tx WHERE sender = '{}' OR recipient = '{}' ORDER BY block_number {}, tx_index {} LIMIT {} OFFSET {}".format(address, address, order_by, order_by, limit, offset)

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
