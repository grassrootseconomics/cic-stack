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


#def test_resend_inplace(
#    default_chain_spec,
#    init_database,
#    init_w3,
#    celery_session_worker,
#    ):
#    
#    chain_str = str(default_chain_spec)
#    c = RpcClient(default_chain_spec)
#    
#    sigs = []
#
#    gas_provider = c.gas_provider()
#
#    s_nonce = celery.signature(
#        'cic_eth.eth.nonce.reserve_nonce',
#        [
#            init_w3.eth.accounts[0],
#            gas_provider,
#            ],
#        queue=None,
#        )
#    s_refill = celery.signature(
#        'cic_eth.eth.gas.refill_gas',
#        [
#            chain_str,
#            ],
#        queue=None,
#            )
#    s_nonce.link(s_refill)
#    t = s_nonce.apply_async()
#    t.get()
#    for r in t.collect():
#        pass
#    assert t.successful()
#
#    q = init_database.query(Otx)
#    q = q.join(TxCache)
#    q = q.filter(TxCache.recipient==init_w3.eth.accounts[0])
#    o = q.first()
#    tx_raw = o.signed_tx
#
#    tx_dict = unpack(bytes.fromhex(tx_raw), default_chain_spec)
#    gas_price_before = tx_dict['gasPrice'] 
#
#    s = celery.signature(
#        'cic_eth.admin.ctrl.lock_send',
#        [
#            chain_str,
#            init_w3.eth.accounts[0],
#            ],
#        queue=None,
#            )
#    t = s.apply_async()
#    t.get()
#    assert t.successful()
#
#    api = AdminApi(c, queue=None)
#    t = api.resend(tx_dict['hash'], chain_str, unlock=True)
#    t.get()
#    i = 0
#    tx_hash_new_hex = None
#    for r in t.collect():
#        tx_hash_new_hex = r[1]
#    assert t.successful()
#  
#    tx_raw_new = get_tx(tx_hash_new_hex) 
#    logg.debug('get {}'.format(tx_raw_new))
#    tx_dict_new = unpack(bytes.fromhex(tx_raw_new['signed_tx']), default_chain_spec)
#    assert tx_hash_new_hex != tx_dict['hash']
#    assert tx_dict_new['gasPrice'] > gas_price_before
#
#    tx_dict_after = get_tx(tx_dict['hash'])
#
#    logg.debug('logggg {}'.format(status_str(tx_dict_after['status'])))
#    assert tx_dict_after['status'] & StatusBits.MANUAL


#def test_check_fix_nonce(
#    default_chain_spec,
#    init_database,
#    init_eth_account_roles,
#    init_w3,
#    eth_empty_accounts,
#    celery_session_worker,
#    ):
#
#    chain_str = str(default_chain_spec)
#    
#    sigs = []
#    for i in range(5):
#        s = celery.signature(
#            'cic_eth.eth.gas.refill_gas',
#            [
#                eth_empty_accounts[i],
#                chain_str,
#                ],
#            queue=None,
#                )
#        sigs.append(s)
#
#    t = celery.group(sigs)()
#    txs = t.get()
#    assert t.successful()
#
#    tx_hash = web3.Web3.keccak(hexstr=txs[2])
#    c = RpcClient(default_chain_spec)
#    api = AdminApi(c, queue=None)
#    address = init_eth_account_roles['eth_account_gas_provider']
#    nonce_spec = api.check_nonce(address)
#    assert nonce_spec['nonce']['network'] == 0
#    assert nonce_spec['nonce']['queue'] == 4
#    assert nonce_spec['nonce']['blocking'] == None
#
#    s_set = celery.signature(
#            'cic_eth.queue.tx.set_rejected',
#            [
#                tx_hash.hex(),
#                ],
#            queue=None,
#            )
#    t = s_set.apply_async()
#    t.get()
#    t.collect()
#    assert t.successful()
#
#
#    nonce_spec = api.check_nonce(address)
#    assert nonce_spec['nonce']['blocking'] == 2
#    assert nonce_spec['tx']['blocking'] == tx_hash.hex()
#
#    t = api.fix_nonce(address, nonce_spec['nonce']['blocking'])
#    t.get()
#    t.collect()
#    assert t.successful()
#
#    for tx in txs[3:]:
#        tx_hash = web3.Web3.keccak(hexstr=tx)
#        tx_dict = get_tx(tx_hash.hex())
#        assert tx_dict['status'] == StatusEnum.OVERRIDDEN
#
#


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
