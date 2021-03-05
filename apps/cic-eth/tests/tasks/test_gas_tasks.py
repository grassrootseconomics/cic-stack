# standard imports
import logging
import time

# third-party imports
import pytest
import celery
from web3.exceptions import ValidationError

# local imports
from cic_eth.db.enum import StatusEnum
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.base import SessionBase
from cic_eth.eth.task import sign_and_register_tx
from cic_eth.eth.task import sign_tx
from cic_eth.eth.token import TokenTxFactory
from cic_eth.eth.token import TxFactory
from cic_eth.eth.token import cache_transfer_data
from cic_eth.eth.rpc import RpcClient
from cic_eth.queue.tx import create as queue_create
from cic_eth.error import OutOfGasError
from cic_eth.db.models.role import AccountRole
from cic_eth.error import AlreadyFillingGasError

logg = logging.getLogger()


def test_refill_gas(
    default_chain_spec,
    init_eth_tester,
    init_rpc,
    init_w3,
    init_database,
    cic_registry,
    init_eth_account_roles,
    celery_session_worker,
    eth_empty_accounts,
        ):

    provider_address = AccountRole.get_address('GAS_GIFTER', init_database)
    receiver_address = eth_empty_accounts[0]

    c = init_rpc
    refill_amount = c.refill_amount()

    balance = init_rpc.w3.eth.getBalance(receiver_address)
    s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                eth_empty_accounts[0],
                provider_address,
                ],
            queue=None,
            )
    s_refill = celery.signature(
            'cic_eth.eth.tx.refill_gas',
            [
                str(default_chain_spec),
            ],
            queue=None,
            )

    s_nonce.link(s_refill)
    t = s_nonce.apply_async()
    r = t.get()
    for c in t.collect():
        pass
    assert t.successful()

    q = init_database.query(Otx)
    q = q.join(TxCache)
    q = q.filter(TxCache.recipient==receiver_address)
    o = q.first()
    signed_tx = o.signed_tx

    s = celery.signature(
            'cic_eth.eth.tx.send',
            [
                [signed_tx],
                str(default_chain_spec),
            ],
            )
    t = s.apply_async()
    r = t.get()
    t.collect()
    assert t.successful()

    init_eth_tester.mine_block()
    balance_new = init_rpc.w3.eth.getBalance(receiver_address)
    assert balance_new == (balance + refill_amount)

    # Verify that entry is added in TxCache
    q = init_database.query(Otx)
    q = q.join(TxCache)
    q = q.filter(TxCache.recipient==receiver_address)
    r = q.first()
    init_database.commit()
    
    assert r.status == StatusEnum.SENT


def test_refill_deduplication(
    default_chain_spec,
    init_rpc,
    init_w3,
    init_database,
    init_eth_account_roles,
    cic_registry,
    celery_session_worker,
    eth_empty_accounts,
        ):

    provider_address = AccountRole.get_address('ETH_GAS_PROVIDER_ADDRESS', init_database)
    receiver_address = eth_empty_accounts[0]

    c = init_rpc
    refill_amount = c.refill_amount()

    s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                receiver_address,
                provider_address,
                ],
            queue=None,
            )
    s_refill = celery.signature(
            'cic_eth.eth.tx.refill_gas',
            [
                str(default_chain_spec),
            ],
            queue=None,
            )

    s_nonce.link(s_refill)
    t = s_nonce.apply_async()
    r = t.get()
    for e in t.collect():
        pass
    assert t.successful()

    s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                receiver_address,
                provider_address,
                ],
            queue=None,
            )
    s_refill = celery.signature(
            'cic_eth.eth.tx.refill_gas',
            [
                str(default_chain_spec),
                ],
            )

    s_nonce.link(s_refill)
    t = s_nonce.apply_async()
    #with pytest.raises(AlreadyFillingGasError):
    t.get()
    for e in t.collect():
        pass
    assert t.successful()
    logg.warning('TODO: complete test by checking that second tx had zero value')


# TODO: check gas is part of the transfer chain, and we cannot create the transfer nonce by uuid before the task. Test is subsumed by transfer task test, but should be tested in isolation
#def test_check_gas(
#    default_chain_spec,
#    init_eth_tester,
#    init_w3,
#    init_rpc,
#    eth_empty_accounts,
#    init_database,
#    cic_registry,
#    celery_session_worker,
#    bancor_registry,
#    bancor_tokens,
#        ):
#
#    provider_address = init_w3.eth.accounts[0]
#    gas_receiver_address = eth_empty_accounts[0]
#    token_receiver_address = init_w3.eth.accounts[1]
#    
##    c = init_rpc
##    txf = TokenTxFactory(gas_receiver_address, c)
##    tx_transfer = txf.transfer(bancor_tokens[0], token_receiver_address, 42, default_chain_spec, 'foo')
##
##    (tx_hash_hex, tx_signed_raw_hex) = sign_and_register_tx(tx_transfer, str(default_chain_spec), None)
#
#    token_data = [
#                    {
#                        'address': bancor_tokens[0],
#                        },
#                    ]
#
#    s_nonce = celery.signature(
#            'cic_eth.eth.tx.reserve_nonce',
#            [
#                token_data,
#                init_w3.eth.accounts[0],
#                ],
#            queue=None,
#            )
#    s_transfer = celery.signature(
#            'cic_eth.eth.token.transfer',
#            [
#                init_w3.eth.accounts[0],
#                init_w3.eth.accounts[1],
#                1024,
#                str(default_chain_spec),
#                ],
#            queue=None,
#            )
#
#    gas_price = c.gas_price()
#    gas_limit = tx_transfer['gas']
#
#    s = celery.signature(
#            'cic_eth.eth.tx.check_gas',
#            [
#                [tx_hash_hex],
#                str(default_chain_spec),
#                [],
#                gas_receiver_address,
#                gas_limit * gas_price,
#                ],
#            )
#    s_nonce.link(s_transfer)
#    t = s_nonce.apply_async()
#    with pytest.raises(OutOfGasError):
#        r = t.get()
#    #assert len(r) == 0
#
#    time.sleep(1)
#    t.collect()
#
#    session = SessionBase.create_session()
#    q = session.query(Otx)
#    q = q.filter(Otx.tx_hash==tx_hash_hex)
#    r = q.first()
#    session.close()
#    assert r.status == StatusEnum.WAITFORGAS


def test_resend_with_higher_gas(
    default_chain_spec,
    init_eth_tester,
    init_w3,
    init_rpc,
    init_database,
    cic_registry,
    celery_session_worker,
    bancor_registry,
    bancor_tokens,
    ):

    c = init_rpc

    token_data = {
                'address': bancor_tokens[0],
                }

    s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                [token_data],
                init_w3.eth.accounts[0],
                ],
            queue=None,
            )
    s_transfer = celery.signature(
            'cic_eth.eth.token.transfer',
            [
                init_w3.eth.accounts[0],
                init_w3.eth.accounts[1],
                1024,
                str(default_chain_spec),
                ],
            queue=None,
            )

#    txf = TokenTxFactory(init_w3.eth.accounts[0], c)

#    tx_transfer = txf.transfer(bancor_tokens[0], init_w3.eth.accounts[1], 1024, default_chain_spec, 'foo')
#    logg.debug('txtransfer {}'.format(tx_transfer))
#    (tx_hash_hex, tx_signed_raw_hex) = sign_tx(tx_transfer, str(default_chain_spec))
#    logg.debug('signed raw {}'.format(tx_signed_raw_hex))
#    queue_create(
#        tx_transfer['nonce'],
#        tx_transfer['from'],
#        tx_hash_hex,
#        tx_signed_raw_hex,
#        str(default_chain_spec),
#            )
#    logg.debug('create {}'.format(tx_transfer['from']))
#    cache_transfer_data(
#        tx_hash_hex,
#        tx_transfer, #_signed_raw_hex,
#            )
    s_nonce.link(s_transfer)
    t = s_nonce.apply_async()
    t.get()
    for r in t.collect():
        pass
    assert t.successful()

    q = init_database.query(Otx)
    q = q.join(TxCache)
    q = q.filter(TxCache.recipient==init_w3.eth.accounts[1])
    o = q.first()
    tx_hash_hex = o.tx_hash

    s_resend = celery.signature(
            'cic_eth.eth.tx.resend_with_higher_gas',
            [
                tx_hash_hex,
                str(default_chain_spec),
            ],
            queue=None,
            )
    
    t = s_resend.apply_async()
    for r in t.collect():
        pass
    assert t.successful()

#
#def test_resume(
#    default_chain_spec,
#    init_eth_tester,
#    w3,
#    w3_account_roles,
#    init_database,
#    bancor_tokens,
#    celery_session_worker,
#    eth_empty_accounts,
#        ):
#
#    txf = TokenTxFactory()
#
#    tx_transfer = txf.transfer(bancor_tokens[0], eth_empty_accounts[1], 1024)
#    (tx_hash_hex, tx_signed_raw_hex) = sign_and_register_tx(tx_transfer)
#
#    resume_tx()
