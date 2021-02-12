# standard imports
import logging
import datetime

# third-party imports
from cic_cache.db.models.base import SessionBase

logg = logging.getLogger()


def list_transactions_mined(session, offset, limit):
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


def list_transactions_account_mined(session, address, offset, limit):
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
    s = "SELECT block_number, tx_index FROM tx WHERE sender = '{}' OR recipient = '{}' block_number DESC, tx_index DESC LIMIT {} OFFSET {}".format(address, address, limit, offset)
    r = session.execute(s)
    return r


def add_transaction(session, tx_hash, block_number, tx_index, sender, receiver, source_token, destination_token, success, timestamp):
    date_block = datetime.datetime.fromtimestamp(timestamp)
    s = "INSERT INTO tx (tx_hash, block_number, tx_index, sender, recipient, source_token, destination_token, success, date_block) VALUES ('{}', {}, {}, '{}', '{}', '{}', '{}', {}, '{}')".format(
            tx_hash,
            block_number,
            tx_index,
            sender,
            receiver,
            source_token,
            destination_token,
            success,
            date_block,
            )
    session.execute(s)
