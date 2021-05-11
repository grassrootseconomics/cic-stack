"""This module defines functions required to query external components of the cic platform for data relevant to
accounts on the cic-ussd component.
"""

# external imports
import celery
from cic_eth.api import Api

# local imports
from cic_ussd.chain import Chain


def person_metadata(blockchain_address: str):
    """This function asynchronously queries the metadata server for metadata associated with the person data type and
    a given blockchain address.
    :param blockchain_address: Ethereum address of account whose metadata is being queried.
    :type blockchain_address: str, 0x-hex
    """
    s_query_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.query_person_metadata',
        [blockchain_address]
    )
    s_query_person_metadata.apply_async(queue='cic-ussd')


def default_token_data() -> dict:
    """This function queries for the default token's data from the cic_eth tasks exposed over its Api class.
    :return: A dict containing the default token address and it's corresponding symbol.
    :rtype: dict
    """
    chain_str = Chain.spec.__str__()
    cic_eth_api = Api(chain_str=chain_str)
    default_token_request_task = cic_eth_api.default_token()
    return default_token_request_task.get()


def transactions_statement(blockchain_address: str):
    """This function asynchronously queries the cic-eth server to retrieve a chronologically reversed list of
    transactions for an account.
    :param blockchain_address: Ethereum address of account whose transactions is being queried.
    :type blockchain_address:
    """
    chain_str = Chain.spec.__str__()
    cic_eth_api = Api(
        chain_str=chain_str,
        callback_queue='cic-ussd',
        callback_task='cic_ussd.tasks.callback_handler.process_statement_callback',
        callback_param=blockchain_address
    )
    cic_eth_api.list(address=blockchain_address, limit=9)
