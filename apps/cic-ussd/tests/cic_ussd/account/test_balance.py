# standard imports

# external imports
import pytest

# local imports
from cic_ussd.account.balance import calculate_available_balance, get_balances, get_cached_available_balance
from cic_ussd.account.chain import Chain
from cic_ussd.error import CachedDataNotFoundError

# test imports
from tests.helpers.accounts import blockchain_address


def test_async_get_balances(activated_account,
                            celery_session_worker,
                            load_chain_spec,
                            load_config,
                            mock_async_balance_api_query):
    blockchain_address = activated_account.blockchain_address
    chain_str = Chain.spec.__str__()
    token_symbol = load_config.get('TEST_TOKEN_SYMBOL')
    get_balances(blockchain_address, chain_str, token_symbol, asynchronous=True)
    assert mock_async_balance_api_query.get('address') == blockchain_address
    assert mock_async_balance_api_query.get('token_symbol') == token_symbol


def test_sync_get_balances(activated_account,
                           balances,
                           celery_session_worker,
                           load_chain_spec,
                           load_config,
                           mock_sync_balance_api_query):
    blockchain_address = activated_account.blockchain_address
    chain_str = Chain.spec.__str__()
    token_symbol = load_config.get('TEST_TOKEN_SYMBOL')
    res = get_balances(blockchain_address, chain_str, token_symbol, asynchronous=False)
    assert res == balances


@pytest.mark.parametrize('balance_incoming, balance_network, balance_outgoing, available_balance', [
    (0, 50000000, 0, 50.00),
    (5000000, 89000000, 67000000, 27.00)
])
def test_calculate_available_balance(activated_account,
                                     available_balance,
                                     balance_incoming,
                                     balance_network,
                                     balance_outgoing,
                                     cache_balances,
                                     cache_default_token_data,
                                     load_chain_spec):
    balances = {
        'address': activated_account.blockchain_address,
        'converters': [],
        'balance_network': balance_network,
        'balance_outgoing': balance_outgoing,
        'balance_incoming': balance_incoming
    }
    assert calculate_available_balance(balances) == available_balance


def test_get_cached_available_balance(activated_account,
                                      balances,
                                      cache_balances,
                                      cache_default_token_data,
                                      load_chain_spec):
    cached_available_balance = get_cached_available_balance(activated_account.blockchain_address)
    available_balance = calculate_available_balance(balances[0])
    assert cached_available_balance == available_balance
    address = blockchain_address()
    with pytest.raises(CachedDataNotFoundError) as error:
        cached_available_balance = get_cached_available_balance(address)
        assert cached_available_balance is None
    assert str(error.value) == f'No cached available balance for address: {address}'
