# standard imports
import json
import logging
from typing import Union

# third-party imports
import celery
from cic_eth.api import Api

# local imports
from cic_ussd.error import CachedDataNotFoundError
from cic_ussd.redis import create_cached_data_key, get_cached_data
from cic_ussd.conversions import from_wei

logg = logging.getLogger()


class BalanceManager:

    def __init__(self, address: str, chain_str: str, token_symbol: str):
        """
        :param address: Ethereum address of account whose balance is being queried
        :type address: str, 0x-hex
        :param chain_str: The chain name and network id.
        :type chain_str: str
        :param token_symbol: ERC20 token symbol of whose balance is being queried
        :type token_symbol: str
        """
        self.address = address
        self.chain_str = chain_str
        self.token_symbol = token_symbol

    def get_balances(self, asynchronous: bool = False) -> Union[celery.Task, dict]:
        """
        This function queries cic-eth for an account's balances, It provides a means to receive the balance either
        asynchronously or synchronously depending on the provided asynchronous value from the function's caller. It
        returns a dictionary containing network, outgoing and incoming balances when synchronously called.
        :param asynchronous: Boolean value checking whether to return balances asynchronously
        :type asynchronous: bool
        :return: dict containing network, outgoing and incoming balances | an async result object from celery.
        :rtype: dict|celery.Task
        """
        if asynchronous:
            cic_eth_api = Api(
                chain_str=self.chain_str,
                callback_queue='cic-ussd',
                callback_task='cic_ussd.tasks.callback_handler.process_balances_callback',
                callback_param=''
            )
            return cic_eth_api.balance(address=self.address, token_symbol=self.token_symbol)
        else:
            cic_eth_api = Api(chain_str=self.chain_str)
            balance_request_task = cic_eth_api.balance(
                address=self.address,
                token_symbol=self.token_symbol)
            return balance_request_task.get()[0]


def operational_balance(balances: dict) -> float:
    """This function computes the operational balance at an instance in the system by providing the difference of the
    outgoing balance from the sum of incoming and network balances.
    :param balances: A dictionary containing incoming, outgoing and network balances.
    :type balances: dict
    :return: The operational balance of the account at the instance of querying.
    :rtype: float
    """
    incoming_balance = balances.get('balance_incoming')
    outgoing_balance = balances.get('balance_outgoing')
    network_balance = balances.get('balance_network')

    balance = (network_balance + incoming_balance) - outgoing_balance
    return from_wei(value=balance)


def cached_operational_balance(blockchain_address: str) -> float:
    """This function retrieves the cached balances data from redis cache and computes the operational balance from
    the cached data.
    :param blockchain_address: Ethereum address of the account whose balance data is being retrieved.
    :type blockchain_address: str, 0x-hex
    :return: The operational balance of the account as per cached balance data.
    :rtype: float
    :raises CachedDataNotFoundError
    """
    key = create_cached_data_key(
        identifier=bytes.fromhex(blockchain_address[2:]),
        salt=':cic.balances_data'
    )
    cached_balance = get_cached_data(key=key)
    if cached_balance:
        balance = operational_balance(balances=json.loads(cached_balance))
        return balance
    else:
        raise CachedDataNotFoundError('Cached operational balance not found.')
