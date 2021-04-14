# standard imports
import os
import logging
import time

# external imports
import pytest
import celery
from cic_eth_registry.erc20 import ERC20Token
from chainlib.chain import ChainSpec

# local imports
from cic_eth.api import Api

logg = logging.getLogger(__name__)


def test_account_api(
        default_chain_spec,
        init_database,
        init_eth_rpc,
        account_registry,
        custodial_roles,
        celery_session_worker,
        ):
    api = Api(str(default_chain_spec), callback_param='accounts', callback_task='cic_eth.callbacks.noop.noop', queue=None)
    t = api.create_account('', register=False)
    t.get_leaf()
    assert t.successful()


def test_transfer_api(
        default_chain_spec,
        eth_rpc,
        init_database,
        foo_token,
        custodial_roles,
        agent_roles,
        cic_registry,
        register_tokens,
        register_lookups,
        celery_session_worker,
        ):

    #token = CICRegistry.get_address(default_chain_spec, bancor_tokens[0])
    foo_token_cache = ERC20Token(default_chain_spec, eth_rpc, foo_token)

    api = Api(str(default_chain_spec), callback_param='transfer', callback_task='cic_eth.callbacks.noop.noop', queue=None)
    t = api.transfer(custodial_roles['FOO_TOKEN_GIFTER'], agent_roles['ALICE'], 1024, foo_token_cache.symbol)
    t.get_leaf()
    assert t.successful()


@pytest.mark.skip()
def test_convert_api(
        default_chain_spec,
        init_w3,
        cic_registry,
        init_database,
        foo_token,
        bar_token,
        celery_session_worker,
        ):
    
    token_alice = CICRegistry.get_address(default_chain_spec, bancor_tokens[0])
    token_bob = CICRegistry.get_address(default_chain_spec, bancor_tokens[1])

    api = Api(str(default_chain_spec), callback_param='convert', callback_task='cic_eth.callbacks.noop.noop', queue=None)
    t = api.convert(custodial_roles['FOO_TOKEN_GIFTER'], 110, 100, foo_token_cache.symbol, bar_token_cache.symbol)
    t.get_leaf()
    assert t.successful()


@pytest.mark.skip()
def test_convert_transfer_api(
        default_chain_spec,
        init_w3,
        cic_registry,
        init_database,
        bancor_registry,
        bancor_tokens,
        celery_session_worker,
        ):

    token_alice = CICRegistry.get_address(default_chain_spec, bancor_tokens[0])
    token_bob = CICRegistry.get_address(default_chain_spec, bancor_tokens[1])

    api = Api(str(default_chain_spec), callback_param='convert_transfer', callback_task='cic_eth.callbacks.noop.noop', queue=None)
    t = api.convert_transfer(init_w3.eth.accounts[2], init_w3.eth.accounts[4], 110, 100, token_alice.symbol(), token_bob.symbol())
    t.get()
    for r in t.collect():
        print(r)
    assert t.successful()


def test_refill_gas(
        default_chain_spec,
        init_database,
        eth_empty_accounts,
        init_eth_rpc,
        custodial_roles,
        celery_session_worker,
        ):

    api = Api(str(default_chain_spec), callback_param='refill_gas', callback_task='cic_eth.callbacks.noop.noop', queue=None)
    t = api.refill_gas(eth_empty_accounts[0])
    t.get()
    for r in t.collect():
        print(r)
    assert t.successful()


def test_ping(
        default_chain_spec,
        celery_session_worker,
        ):
    api = Api(str(default_chain_spec), callback_param='ping', callback_task='cic_eth.callbacks.noop.noop', queue=None)
    t = api.ping('pong')
    t.get()
    for r in t.collect():
        print(r)
    assert t.successful()
