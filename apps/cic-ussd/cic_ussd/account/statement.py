# standard imports
import datetime
import logging
from typing import Optional

# external imports
import celery
from chainlib.hash import strip_0x
from cic_eth.api import Api

# local import
from cic_ussd.account.chain import Chain
from cic_ussd.account.transaction import from_wei
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.translation import translation_for

logg = logging.getLogger(__name__)


def filter_statement_transactions(transaction_list: list) -> list:
    """This function parses a transaction list and removes all transactions that entail interactions with the
    zero address as the source transaction.
    :param transaction_list: Array containing transaction objects.
    :type transaction_list: list
    :return: Transactions exclusive of the zero address transactions.
    :rtype: list
    """
    return [tx for tx in transaction_list if tx.get('source_token') != '0x0000000000000000000000000000000000000000']


def generate(querying_party: str, queue: Optional[str], transaction: dict):
    """
    :param querying_party:
    :type querying_party:
    :param queue:
    :type queue:
    :param transaction:
    :type transaction:
    :return:
    :rtype:
    """
    s_generate_statement = celery.signature(
        'cic_ussd.tasks.processor.generate_statement', [querying_party, transaction], queue=queue
    )
    s_generate_statement.apply_async()


def get_cached_statement(blockchain_address: str) -> bytes:
    """This function retrieves an account's cached record of a specific number of transactions in chronological order.
    :param blockchain_address: Bytes representation of the hex value of an account's blockchain address.
    :type blockchain_address: bytes
    :return: Account's transactions statements.
    :rtype: str
    """
    identifier = bytes.fromhex(strip_0x(blockchain_address))
    key = cache_data_key(identifier=identifier, salt=':cic.statement')
    return get_cached_data(key=key)


def parse_statement_transactions(statement: list):
    """This function extracts information for transaction objects loaded from the redis cache and structures the data in
    a format that is appropriate for the ussd interface.
    :param statement: A list of transaction objects.
    :type statement: list
    :return:
    :rtype:
    """
    parsed_transactions = []
    for transaction in statement:
        action_tag = transaction.get('action_tag')
        amount = from_wei(transaction.get('token_value'))
        direction_tag = transaction.get('direction_tag')
        token_symbol = transaction.get('token_symbol')
        metadata_id = transaction.get('metadata_id')
        timestamp = datetime.datetime.now().strftime('%d/%m/%y, %H:%M')
        transaction_repr = f'{action_tag} {amount} {token_symbol} {direction_tag} {metadata_id} {timestamp}'
        parsed_transactions.append(transaction_repr)
    return parsed_transactions


def query_statement(blockchain_address: str, limit: int = 9):
    """This function queries cic-eth for a set of chronologically ordered number of transactions associated with
    an account.
    :param blockchain_address: Ethereum address associated with an account.
    :type blockchain_address: str, 0x-hex
    :param limit: Number of transactions to be returned.
    :type limit: int
    """
    logg.debug(f'retrieving balance for address: {blockchain_address}')
    chain_str = Chain.spec.__str__()
    cic_eth_api = Api(
        chain_str=chain_str,
        callback_queue='cic-ussd',
        callback_task='cic_ussd.tasks.callback_handler.statement_callback',
        callback_param=blockchain_address
    )
    cic_eth_api.list(address=blockchain_address, limit=limit)


def statement_transaction_set(preferred_language: str, transaction_reprs: list):
    """
    :param preferred_language:
    :type preferred_language:
    :param transaction_reprs:
    :type transaction_reprs:
    :return:
    :rtype:
    """
    if not transaction_reprs:
        return translation_for('helpers.no_transaction_history', preferred_language)
    return ''.join(f'{transaction_repr}\n' for transaction_repr in transaction_reprs)
