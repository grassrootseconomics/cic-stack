# standard imports

import json
import logging
from typing import Optional

# third-party imports
from cic_eth.api import Api
from cic_eth_aux.erc20_demurrage_token.api import Api as DemurrageApi

# local imports
from cic_ussd.account.transaction import from_wei
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.error import CachedDataNotFoundError

logg = logging.getLogger()


def get_balances(address: str,
                 chain_str: str,
                 token_symbol: str,
                 asynchronous: bool = False,
                 callback_param: any = None,
                 callback_queue='cic-ussd',
                 callback_task='cic_ussd.tasks.callback_handler.balances_callback') -> Optional[list]:
    """This function queries cic-eth for an account's balances, It provides a means to receive the balance either
    asynchronously or synchronously.. It returns a dictionary containing the network, outgoing and incoming balances.
    :param address: Ethereum address of an account.
    :type address: str, 0x-hex
    :param chain_str: The chain name and network id.
    :type chain_str: str
    :param asynchronous: Boolean value checking whether to return balances asynchronously.
    :type asynchronous: bool
    :param callback_param: Data to be sent along with the callback containing balance data.
    :type callback_param: any
    :param callback_queue:
    :type callback_queue:
    :param callback_task: A celery task path to which callback data should be sent.
    :type callback_task: str
    :param token_symbol: ERC20 token symbol of the account whose balance is being queried.
    :type token_symbol: str
    :return: A list containing balance data if called synchronously. | None
    :rtype: list | None
    """
    logg.debug(f'retrieving balance for address: {address}')
    if asynchronous:
        cic_eth_api = Api(
            chain_str=chain_str,
            callback_queue=callback_queue,
            callback_task=callback_task,
            callback_param=callback_param
        )
        cic_eth_api.balance(address=address, token_symbol=token_symbol)
    else:
        cic_eth_api = Api(chain_str=chain_str)
        balance_request_task = cic_eth_api.balance(
            address=address,
            token_symbol=token_symbol)
        return balance_request_task.get()


def calculate_available_balance(balances: dict) -> float:
    """This function calculates an account's balance at a specific point in time by computing the difference from the
    outgoing balance and the sum of the incoming and network balances.
    :param balances: incoming, network and outgoing balances.
    :type balances: dict
    :return: Token value of the available balance.
    :rtype: float
    """
    incoming_balance = balances.get('balance_incoming')
    outgoing_balance = balances.get('balance_outgoing')
    network_balance = balances.get('balance_network')

    available_balance = (network_balance + incoming_balance) - outgoing_balance
    return from_wei(value=available_balance)


def get_adjusted_balance(balance: int, chain_str: str, timestamp: int, token_symbol: str):
    """
    :param balance:
    :type balance:
    :param chain_str:
    :type chain_str:
    :param timestamp:
    :type timestamp:
    :param token_symbol:
    :type token_symbol:
    :return:
    :rtype:
    """
    logg.debug(f'retrieving adjusted balance on chain: {chain_str}')
    demurrage_api = DemurrageApi(chain_str=chain_str)
    return demurrage_api.get_adjusted_balance(token_symbol, balance, timestamp).result


def get_cached_available_balance(blockchain_address: str) -> float:
    """This function attempts to retrieve balance data from the redis cache.
    :param blockchain_address: Ethereum address of an account.
    :type blockchain_address: str
    :raises CachedDataNotFoundError: No cached balance data could be found.
    :return: Operational balance of an account.
    :rtype: float
    """
    identifier = bytes.fromhex(blockchain_address)
    key = cache_data_key(identifier, salt=':cic.balances')
    cached_balances = get_cached_data(key=key)
    if cached_balances:
        return calculate_available_balance(json.loads(cached_balances))
    else:
        raise CachedDataNotFoundError(f'No cached available balance for address: {blockchain_address}')


def get_cached_adjusted_balance(identifier: bytes):
    """
    :param identifier:
    :type identifier:
    :return:
    :rtype:
    """
    key = cache_data_key(identifier, ':cic.adjusted_balance')
    return get_cached_data(key)
