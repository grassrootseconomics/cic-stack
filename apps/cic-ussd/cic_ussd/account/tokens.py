# standard imports
import hashlib
import json
import logging
from typing import Optional, Union

# external imports
from cic_eth.api import Api
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.account.balance import get_cached_available_balance
from cic_ussd.account.chain import Chain
from cic_ussd.cache import cache_data, cache_data_key, get_cached_data
from cic_ussd.error import CachedDataNotFoundError, SeppukuError
from cic_ussd.metadata.tokens import query_token_info, query_token_metadata
from cic_ussd.processor.poller import wait_for_cache

logg = logging.getLogger(__file__)


def collate_token_metadata(token_info: dict, token_metadata: dict) -> dict:
    """
    :param token_info:
    :type token_info:
    :param token_metadata:
    :type token_metadata:
    :return:
    :rtype:
    """
    logg.debug(f'Collating token info: {token_info} and token metadata: {token_metadata}')
    description = token_info.get('description')
    issuer = token_info.get('issuer')
    location = token_metadata.get('location')
    contact = token_metadata.get('contact')
    return {
        'description': description,
        'issuer': issuer,
        'location': location,
        'contact': contact
    }


def create_account_tokens_list(blockchain_address: str):
    """
    :param blockchain_address:
    :type blockchain_address:
    :return:
    :rtype:
    """
    token_symbols_list = get_cached_token_symbol_list(blockchain_address=blockchain_address)
    token_list_entries = []
    if token_symbols_list:
        logg.debug(f'Token symbols: {token_symbols_list} for account: {blockchain_address}')
        for token_symbol in token_symbols_list:
            logg.debug(f'Processing token data for: {token_symbol}')
            key = cache_data_key(token_symbol.encode('utf-8'), MetadataPointer.TOKEN_DATA)
            token_data = get_cached_data(key)
            token_data = json.loads(token_data)
            logg.debug(f'Retrieved token data: {token_data} for: {token_symbol}')
            token_name = token_data.get('name')
            entry = {'name': token_name}
            token_symbol = token_data.get('symbol')
            entry['symbol'] = token_symbol
            token_issuer = token_data.get('issuer')
            entry['issuer'] = token_issuer
            token_contact = token_data['contact'].get('phone')
            entry['contact'] = token_contact
            token_location = token_data.get('location')
            entry['location'] = token_location
            decimals = token_data.get('decimals')
            identifier = [bytes.fromhex(blockchain_address), token_symbol.encode('utf-8')]
            wait_for_cache(identifier, f'Cached available balance for token: {token_symbol}', MetadataPointer.BALANCES)
            token_balance = get_cached_available_balance(decimals=decimals, identifier=identifier)
            entry['balance'] = token_balance
            token_list_entries.append(entry)
    account_tokens_list = order_account_tokens_list(token_list_entries, bytes.fromhex(blockchain_address))
    key = cache_data_key(bytes.fromhex(blockchain_address), MetadataPointer.TOKEN_DATA_LIST)
    cache_data(key, json.dumps(account_tokens_list))


def get_active_token_symbol(blockchain_address: str):
    """
    :param blockchain_address:
    :type blockchain_address:
    :return:
    :rtype:
    """
    identifier = bytes.fromhex(blockchain_address)
    key = cache_data_key(identifier=identifier, salt=MetadataPointer.TOKEN_ACTIVE)
    active_token_symbol = get_cached_data(key)
    if not active_token_symbol:
        raise CachedDataNotFoundError('No active token set.')
    return active_token_symbol


def get_cached_token_data(blockchain_address: str, token_symbol: str):
    """
    :param blockchain_address:
    :type blockchain_address:
    :param token_symbol:
    :type token_symbol:
    :return:
    :rtype:
    """
    key = cache_data_key(token_symbol.encode("utf-8"), MetadataPointer.TOKEN_DATA)
    logg.debug(f'Retrieving token data for: {token_symbol} at: {key}')
    token_data = get_cached_data(key)
    return json.loads(token_data)


def get_cached_default_token(chain_str: str) -> Optional[str]:
    """This function attempts to retrieve the default token's data from the redis cache.
    :param chain_str: chain name and network id.
    :type chain_str: str
    :return:
    :rtype:
    """
    logg.debug(f'Retrieving default token from cache for chain: {chain_str}')
    key = cache_data_key(identifier=chain_str.encode('utf-8'), salt=MetadataPointer.TOKEN_DEFAULT)
    return get_cached_data(key=key)


def get_default_token_symbol():
    """This function attempts to retrieve the default token's symbol from cached default token's data.
    :raises SeppukuError: The system should terminate itself because the default token is required for an appropriate
    system state.
    :return: Default token's symbol.
    :rtype: str
    """
    chain_str = Chain.spec.__str__()
    if cached_default_token := get_cached_default_token(chain_str):
        default_token_data = json.loads(cached_default_token)
        return default_token_data.get('symbol')
    else:
        logg.warning('Cached default token data not found. Attempting retrieval from default token API')
        if default_token_data := query_default_token(chain_str):
            return default_token_data.get('symbol')
        else:
            raise SeppukuError(f'Could not retrieve default token for: {chain_str}')


def get_cached_token_symbol_list(blockchain_address: str) -> Optional[list]:
    """
    :param blockchain_address:
    :type blockchain_address:
    :return:
    :rtype:
    """
    key = cache_data_key(identifier=bytes.fromhex(blockchain_address), salt=MetadataPointer.TOKEN_SYMBOLS_LIST)
    token_symbols_list = get_cached_data(key)
    if token_symbols_list:
        return json.loads(token_symbols_list)
    return token_symbols_list


def get_cached_token_data_list(blockchain_address: str) -> Optional[list]:
    """
    :param blockchain_address:
    :type blockchain_address:
    :return:
    :rtype:
    """
    key = cache_data_key(bytes.fromhex(blockchain_address), MetadataPointer.TOKEN_DATA_LIST)
    token_data_list = get_cached_data(key)
    if token_data_list:
        return json.loads(token_data_list)
    return token_data_list


def handle_token_symbol_list(blockchain_address: str, token_symbol: str):
    """
    :param blockchain_address:
    :type blockchain_address:
    :param token_symbol:
    :type token_symbol:
    :return:
    :rtype:
    """
    token_symbol_list = get_cached_token_symbol_list(blockchain_address)
    if token_symbol_list:
        if token_symbol not in token_symbol_list:
            token_symbol_list.append(token_symbol)
    else:
        token_symbol_list = [token_symbol]

    identifier = bytes.fromhex(blockchain_address)
    key = cache_data_key(identifier=identifier, salt=MetadataPointer.TOKEN_SYMBOLS_LIST)
    data = json.dumps(token_symbol_list)
    cache_data(key, data)


def hashed_token_proof(token_proof: Union[dict, str]) -> str:
    """
    :param token_proof:
    :type token_proof:
    :return:
    :rtype:
    """
    if isinstance(token_proof, dict):
        token_proof = json.dumps(token_proof, separators=(',', ':'))
    logg.debug(f'Hashing token proof: {token_proof}')
    hash_object = hashlib.new("sha256")
    hash_object.update(token_proof.encode('utf-8'))
    return hash_object.digest().hex()


def order_account_tokens_list(account_tokens_list: list, identifier: bytes) -> list:
    """
    :param account_tokens_list:
    :type account_tokens_list:
    :param identifier:
    :type identifier:
    :return:
    :rtype:
    """
    ordered_tokens_list = []
    # get last sent token
    key = cache_data_key(identifier=identifier, salt=MetadataPointer.TOKEN_LAST_SENT)
    last_sent_token_symbol = get_cached_data(key)

    # get last received token
    key = cache_data_key(identifier=identifier, salt=MetadataPointer.TOKEN_LAST_RECEIVED)
    last_received_token_symbol = get_cached_data(key)

    last_sent_token_data, remaining_accounts_token_list = remove_from_account_tokens_list(account_tokens_list, last_sent_token_symbol)
    if last_sent_token_data:
        ordered_tokens_list.append(last_sent_token_data[0])

    last_received_token_data, remaining_accounts_token_list = remove_from_account_tokens_list(remaining_accounts_token_list, last_received_token_symbol)
    if last_received_token_data:
        ordered_tokens_list.append(last_received_token_data[0])

    # order the by balance
    ordered_by_balance = sorted(remaining_accounts_token_list, key=lambda d: d['balance'], reverse=True)
    return ordered_tokens_list + ordered_by_balance


def parse_token_list(account_token_list: list):
    parsed_token_list = []
    for i in range(len(account_token_list)):
        token_symbol = account_token_list[i].get('symbol')
        token_balance = account_token_list[i].get('balance')
        token_data_repr = f'{i+1}. {token_symbol} {token_balance}'
        parsed_token_list.append(token_data_repr)
    return parsed_token_list


def process_token_data(blockchain_address: str, token_symbol: str):
    """

    :param blockchain_address:
    :type blockchain_address:
    :param token_symbol:
    :type token_symbol:
    :return:
    :rtype:
    """
    logg.debug(f'Processing token data for token: {token_symbol}')
    identifier = token_symbol.encode('utf-8')
    query_token_metadata(identifier=identifier)
    token_info = query_token_info(identifier=identifier)
    hashed_token_info = hashed_token_proof(token_proof=token_info)
    hashed_token_symbol = hashed_token_proof(token_symbol)
    query_token_data(blockchain_address=blockchain_address,
                     hashed_proofs=[[hashed_token_info, hashed_token_symbol]],
                     token_symbols=[token_symbol])


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


def query_token_data(blockchain_address: str, hashed_proofs: list, token_symbols: list):
    """"""
    logg.debug(f'Retrieving token metadata for tokens: {", ".join(token_symbols)}')
    api = Api(callback_param=blockchain_address,
              callback_queue='cic-ussd',
              chain_str=Chain.spec.__str__(),
              callback_task='cic_ussd.tasks.callback_handler.token_data_callback')
    api.tokens(token_symbols=token_symbols, proof=hashed_proofs)


def remove_from_account_tokens_list(account_tokens_list: list, token_symbol: str):
    """
    :param account_tokens_list:
    :type account_tokens_list:
    :param token_symbol:
    :type token_symbol:
    :return:
    :rtype:
    """
    removed_token_data = []
    for i in range(len(account_tokens_list)):
        if account_tokens_list[i]['symbol'] == token_symbol:
            removed_token_data.append(account_tokens_list[i])
            del account_tokens_list[i]
            break
    return removed_token_data, account_tokens_list


def set_active_token(blockchain_address: str, token_symbol: str):
    """
    :param blockchain_address:
    :type blockchain_address:
    :param token_symbol:
    :type token_symbol:
    :return:
    :rtype:
    """
    logg.info(f'Active token set to: {token_symbol}')
    key = cache_data_key(identifier=bytes.fromhex(blockchain_address), salt=MetadataPointer.TOKEN_ACTIVE)
    cache_data(key=key, data=token_symbol)


