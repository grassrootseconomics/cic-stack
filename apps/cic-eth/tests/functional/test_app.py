# standard imports
import os
import logging
import time

# third-party imports
import pytest
import celery
from cic_registry import CICRegistry

# platform imports
from cic_eth.api import Api
from cic_eth.eth.factory import TxFactory

logg = logging.getLogger(__name__)

def test_account_api(
        default_chain_spec,
        init_w3,
        init_database,
        init_eth_account_roles,
        celery_session_worker,
        ):
    api = Api(str(default_chain_spec), callback_param='accounts', callback_task='cic_eth.callbacks.noop.noop', queue=None)
    t = api.create_account('', register=False)
    t.get()
    for r in t.collect():
        print(r)
    assert t.successful()


def test_transfer_api(
        default_chain_spec,
        init_w3,
        cic_registry,
        init_database,
        bancor_registry,
        bancor_tokens,
        celery_session_worker,
        ):

    token = CICRegistry.get_address(default_chain_spec, bancor_tokens[0])

    api = Api(str(default_chain_spec), callback_param='transfer', callback_task='cic_eth.callbacks.noop.noop', queue=None)
    t = api.transfer(init_w3.eth.accounts[2], init_w3.eth.accounts[4], 111, token.symbol())
    t.get()
    for r in t.collect():
        print(r)
    assert t.successful()


@pytest.mark.skip()
def test_convert_api(
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

    api = Api(str(default_chain_spec), callback_param='convert', callback_task='cic_eth.callbacks.noop.noop', queue=None)
    t = api.convert(init_w3.eth.accounts[2], 110, 100, token_alice.symbol(), token_bob.symbol())
    for r in t.collect():
        print(r)
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
        cic_registry,
        init_database,
        init_w3,
        celery_session_worker,
        eth_empty_accounts,
        ):

    api = Api(str(default_chain_spec), callback_param='convert_transfer', callback_task='cic_eth.callbacks.noop.noop', queue=None)
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
