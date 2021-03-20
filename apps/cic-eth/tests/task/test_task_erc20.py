# standard imports
import logging

# external imports
import pytest
import celery
from chainlib.eth.erc20 import ERC20
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import (
        receipt,
        TxFormat,
        )

# local imports
from cic_eth.queue.tx import register_tx

logg = logging.getLogger()


def test_otx_cache_transfer(
        default_chain_spec,
        foo_token,
        token_roles,
        agent_roles,
        eth_signer,
        eth_rpc,
        init_database,
        celery_session_worker,
        ):
    nonce_oracle = RPCNonceOracle(token_roles['FOO_TOKEN_OWNER'], eth_rpc)
    c = ERC20(signer=eth_signer, nonce_oracle=nonce_oracle, chain_id=default_chain_spec.chain_id())
    transfer_value = 100 * (10**6)
    (tx_hash_hex, tx_signed_raw_hex) = c.transfer(foo_token, token_roles['FOO_TOKEN_OWNER'], agent_roles['ALICE'], transfer_value, tx_format=TxFormat.RLP_SIGNED)
    register_tx(tx_hash_hex, tx_signed_raw_hex, default_chain_spec, None, session=init_database)

    s = celery.signature(
            'cic_eth.eth.erc20.cache_transfer_data',
            [
                tx_hash_hex,
                tx_signed_raw_hex,
                default_chain_spec.asdict(),
                ],
            queue=None,
            )
    t = s.apply_async()
    r = t.get()

    assert r[0] == tx_hash_hex


def test_erc20_balance_task(
        default_chain_spec,
        foo_token,
        token_roles,
        agent_roles,
        eth_signer,
        eth_rpc,
        celery_session_worker,
        ):

    nonce_oracle = RPCNonceOracle(token_roles['FOO_TOKEN_OWNER'], eth_rpc)
    c = ERC20(signer=eth_signer, nonce_oracle=nonce_oracle, chain_id=default_chain_spec.chain_id())
    transfer_value = 100 * (10**6)
    (tx_hash_hex, o) = c.transfer(foo_token, token_roles['FOO_TOKEN_OWNER'], agent_roles['ALICE'], transfer_value)
    eth_rpc.do(o)
    
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    token_object = {
        'address': foo_token,
            }
    s = celery.signature(
            'cic_eth.eth.erc20.balance',
            [
                [token_object],
                agent_roles['ALICE'],
                default_chain_spec.asdict(),
                ],
            queue=None,
            )
    t = s.apply_async()
    r = t.get()
    assert r[0]['balance_network'] == transfer_value


def test_erc20_transfer_task(
        default_chain_spec,
        foo_token,
        agent_roles,
        custodial_roles,
        eth_signer,
        eth_rpc,
        init_database,
        celery_session_worker,
        ):

    token_object = {
        'address': foo_token,
            }
    transfer_value = 100 * (10 ** 6)

    s_nonce = celery.signature(
        'cic_eth.eth.tx.reserve_nonce',
        [
            [token_object],
            custodial_roles['FOO_TOKEN_GIFTER'],
            ],
        queue=None,
            )
    s_transfer = celery.signature(
            'cic_eth.eth.erc20.transfer',
            [
                custodial_roles['FOO_TOKEN_GIFTER'],
                agent_roles['ALICE'],
                transfer_value,
                default_chain_spec.asdict(),
                ],
            queue=None,
            )
    s_nonce.link(s_transfer)
    t = s_nonce.apply_async()
    r = t.get_leaf()

    logg.debug('result {}'.format(r))


def test_erc20_approve_task(
        default_chain_spec,
        foo_token,
        agent_roles,
        custodial_roles,
        eth_signer,
        eth_rpc,
        init_database,
        celery_session_worker,
        ):

    token_object = {
        'address': foo_token,
            }
    transfer_value = 100 * (10 ** 6)

    s_nonce = celery.signature(
        'cic_eth.eth.tx.reserve_nonce',
        [
            [token_object],
            custodial_roles['FOO_TOKEN_GIFTER'],
            ],
        queue=None,
            )
    s_transfer = celery.signature(
            'cic_eth.eth.erc20.approve',
            [
                custodial_roles['FOO_TOKEN_GIFTER'],
                agent_roles['ALICE'],
                transfer_value,
                default_chain_spec.asdict(),
                ],
            queue=None,
            )
    s_nonce.link(s_transfer)
    t = s_nonce.apply_async()
    r = t.get_leaf()

    logg.debug('result {}'.format(r))
