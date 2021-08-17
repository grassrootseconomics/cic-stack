# standard imports
import json
import logging
from typing import Dict, Optional

# external imports
from cic_eth.api import Api

# local imports
from cic_ussd.account.chain import Chain
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.error import SeppukuError


logg = logging.getLogger(__name__)


def get_cached_default_token(chain_str: str) -> Optional[str]:
    """This function attempts to retrieve the default token's data from the redis cache.
    :param chain_str: chain name and network id.
    :type chain_str: str
    :return:
    :rtype:
    """
    logg.debug(f'Retrieving default token from cache for chain: {chain_str}')
    key = cache_data_key(identifier=chain_str.encode('utf-8'), salt=':cic.default_token_data')
    return get_cached_data(key=key)


def get_default_token_symbol():
    """This function attempts to retrieve the default token's symbol from cached default token's data.
    :raises SeppukuError: The system should terminate itself because the default token is required for an appropriate
    system state.
    :return: Default token's symbol.
    :rtype: str
    """
    chain_str = Chain.spec.__str__()
    cached_default_token = get_cached_default_token(chain_str)
    if cached_default_token:
        default_token_data = json.loads(cached_default_token)
        return default_token_data.get('symbol')
    else:
        logg.warning('Cached default token data not found. Attempting retrieval from default token API')
        default_token_data = query_default_token(chain_str)
        if default_token_data:
            return default_token_data.get('symbol')
        else:
            raise SeppukuError(f'Could not retrieve default token for: {chain_str}')


def query_default_token(chain_str: str):
    """This function synchronously queries cic-eth for the deployed system's default token.
    :param chain_str: Chain name and network id.
    :type chain_str: str
    :return: Token's data.
    :rtype: dict
    """
    logg.debug(f'Querying API for default token on chain: {chain_str}')
    cic_eth_api = Api(chain_str=chain_str)
    default_token_request_task = cic_eth_api.default_token()
    return default_token_request_task.get()
