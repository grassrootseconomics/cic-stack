# standard imports
import os
import logging

# external imports
import celery
import pytest
from chainlib.eth.tx import (
        unpack,
        TxFormat,
        )
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.gas import Gas
from chainlib.eth.address import to_checksum_address
from hexathon import (
        strip_0x,
        add_0x,
        )
from chainqueue.db.models.otx import Otx
from chainqueue.db.models.tx import TxCache
from chainqueue.db.enum import (
        StatusEnum,
        StatusBits,
        status_str,
        )
from chainqueue.query import get_tx

# local imports
from cic_eth.api import AdminApi
from cic_eth.db.models.role import AccountRole
from cic_eth.db.enum import LockEnum
from cic_eth.error import InitializationError
from cic_eth.eth.gas import cache_gas_data
from cic_eth.queue.tx import queue_create

logg = logging.getLogger()


def test_have_account(
    default_chain_spec,
    custodial_roles,
    init_celery_tasks,
    eth_rpc,
    celery_session_worker,
    ):

    api = AdminApi(None, queue=None)
    t = api.have_account(custodial_roles['ALICE'], default_chain_spec)
    assert t.get() != None 

    bogus_address = add_0x(to_checksum_address(os.urandom(20).hex()))
    api = AdminApi(None, queue=None)
    t = api.have_account(bogus_address, default_chain_spec)
    assert t.get() == None


def test_locking(
    default_chain_spec,
    init_database,
    agent_roles,
    init_celery_tasks,
    celery_session_worker,
    ):

    api = AdminApi(None, queue=None)

    t = api.lock(default_chain_spec, agent_roles['ALICE'], LockEnum.SEND)
    t.get()
    t = api.get_lock()
    r = t.get()
    assert len(r) == 1

    t = api.unlock(default_chain_spec, agent_roles['ALICE'], LockEnum.SEND)
    t.get()
    t = api.get_lock()
    r = t.get()
    assert len(r) == 0


def test_tag_account(
    default_chain_spec,
    init_database,
    agent_roles,
    eth_rpc,
    init_celery_tasks,
    celery_session_worker,
    ):

    api = AdminApi(eth_rpc, queue=None)

    t = api.tag_account('foo', agent_roles['ALICE'], default_chain_spec)
    t.get()
    t = api.tag_account('bar', agent_roles['BOB'], default_chain_spec)
    t.get()
    t = api.tag_account('bar', agent_roles['CAROL'], default_chain_spec)
    t.get()

    assert AccountRole.get_address('foo', init_database) == agent_roles['ALICE']
    assert AccountRole.get_address('bar', init_database) == agent_roles['CAROL']


#def test_ready(
#    init_database,
#    agent_roles,
#    eth_rpc,
#    ):
#
#    api = AdminApi(eth_rpc)
#   
#    with pytest.raises(InitializationError):
#        api.ready()
#
#    bogus_account = os.urandom(20)
#    bogus_account_hex = '0x' + bogus_account.hex()
#
#    api.tag_account('ETH_GAS_PROVIDER_ADDRESS', web3.Web3.toChecksumAddress(bogus_account_hex))
#    with pytest.raises(KeyError):
#        api.ready()
#
#    api.tag_account('ETH_GAS_PROVIDER_ADDRESS', eth_empty_accounts[0])
#    api.ready()


def test_tx(
    default_chain_spec,
    cic_registry,
    init_database,
    eth_rpc,
    eth_signer,
    agent_roles,
    contract_roles,
    celery_session_worker,
    ):

    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)
    c = Gas(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, tx_signed_raw_hex) = c.create(agent_roles['ALICE'], agent_roles['BOB'], 1024, tx_format=TxFormat.RLP_SIGNED)
    tx = unpack(bytes.fromhex(strip_0x(tx_signed_raw_hex)), default_chain_spec)
    queue_create(default_chain_spec, tx['nonce'], agent_roles['ALICE'], tx_hash_hex, tx_signed_raw_hex)
    cache_gas_data(tx_hash_hex, tx_signed_raw_hex, default_chain_spec.asdict())

    api = AdminApi(eth_rpc, queue=None, call_address=contract_roles['DEFAULT'])
    tx = api.tx(default_chain_spec, tx_hash=tx_hash_hex)
    logg.warning('code missing to verify tx contents {}'.format(tx))
