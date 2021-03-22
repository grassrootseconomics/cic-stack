# standard imports
import os
import logging
import time

# third-party imports
import pytest
import celery
from chainlib.connection import RPCConnection
from eth_accounts_index import AccountRegistry
from hexathon import strip_0x

# local imports
from cic_eth.error import OutOfGasError
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.base import SessionBase
from cic_eth.db.enum import StatusEnum
from cic_eth.db.enum import StatusEnum
from cic_eth.db.models.nonce import Nonce
from cic_eth.db.models.role import AccountRole

logg = logging.getLogger()


@pytest.mark.skip()
def test_create_account(
        default_chain_spec,
        eth_rpc,
        init_database,
        celery_session_worker,
        caplog,
        ):
    s = celery.signature(
            'cic_eth.eth.account.create',
            [
                'foo',
                default_chain_spec.asdict(),
                ],
            )
    t = s.apply_async()
    r = t.get()

    session = SessionBase.create_session()
    q = session.query(Nonce).filter(Nonce.address_hex==r)
    o = q.first()
    session.close()
    assert o != None
    assert o.nonce == 0

    s = celery.signature(
            'cic_eth.eth.account.have',
            [
                r,
                default_chain_spec.asdict(),
            ],
            )
    t = s.apply_async()
    assert r == t.get()


def test_register_account(
        default_chain_spec,
        account_registry,
        init_database,
        init_eth_tester,
        eth_accounts,
        eth_rpc,
        cic_registry,
        eth_empty_accounts,
        custodial_roles,
        call_sender,
        celery_session_worker,
        ):

    s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                eth_empty_accounts[0],
                custodial_roles['ACCOUNT_REGISTRY_WRITER'],
                ],
            queue=None,
            )
    s_register = celery.signature(
            'cic_eth.eth.account.register',
            [
                default_chain_spec.asdict(),
                custodial_roles['ACCOUNT_REGISTRY_WRITER'],
                ],
            queue=None,
            )
    s_nonce.link(s_register)
    t = s_nonce.apply_async()
    address = t.get()
    for r in t.collect():
        logg.debug('r {}'.format(r))
    assert t.successful()

    session = SessionBase.create_session()
    o = session.query(Otx).first()
    tx_signed_hex = o.signed_tx
    session.close()
   
    s_send = celery.signature(
            'cic_eth.eth.tx.send',
            [
                [tx_signed_hex],
                default_chain_spec.asdict(),
            ],
            queue=None,
            )
    t = s_send.apply_async()
    address = t.get()
    r = t.collect()
    t.successful()

    init_eth_tester.mine_block()

    c = AccountRegistry()
    o = c.have(account_registry, eth_empty_accounts[0], sender_address=call_sender)
    r = eth_rpc.do(o)
    assert int(strip_0x(r), 16) == 1


@pytest.mark.skip()
def test_role_task(
    default_chain_spec,
    init_database,
    celery_session_worker,
        ):

    address = '0x' + os.urandom(20).hex()
    role = AccountRole.set('foo', address)
    init_database.add(role)
    init_database.commit()
    s = celery.signature(
            'cic_eth.eth.account.role',
            [
                address,
                str(default_chain_spec), 
                ],
            )
    t = s.apply_async()
    r = t.get()
    assert r == 'foo'
