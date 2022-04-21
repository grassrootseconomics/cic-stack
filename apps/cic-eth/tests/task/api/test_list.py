# standard imports
import logging

# external imports
import pytest
from chainlib.eth.nonce import RPCNonceOracle
from eth_erc20 import ERC20
from chainlib.eth.tx import receipt
from hexathon import strip_0x

# local imports
from cic_eth.api.api_task import Api
from cic_eth.db.models.nonce import (
        Nonce,
        NonceReservation,
        )

# test imports
from cic_eth.pytest.mock.filter import (
        block_filter,
        tx_filter,
        )

logg = logging.getLogger()


def test_list_tx(
        default_chain_spec,
        init_database,
        cic_registry,
        eth_rpc,
        eth_signer,
        custodial_roles,
        agent_roles,
        foo_token,
        register_tokens,
        register_lookups,
        init_eth_tester,
        celery_session_worker,
        init_celery_tasks,
        ):

    tx_hashes = []

    # external tx
    nonce_oracle = RPCNonceOracle(custodial_roles['FOO_TOKEN_GIFTER'], eth_rpc)
    nonce = nonce_oracle.get_nonce()
    
    q = init_database.query(Nonce)
    q = q.filter(Nonce.address_hex==agent_roles['ALICE'])
    o = q.first()
    o.nonce = nonce
    init_database.add(o)
    init_database.commit()

    # TODO: implement cachenonceoracle instead, this is useless
    # external tx one
    Nonce.next(custodial_roles['FOO_TOKEN_GIFTER'], 'foo', session=init_database)
    init_database.commit()

    init_eth_tester.mine_blocks(13)
    c = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, o) = c.transfer(foo_token, custodial_roles['FOO_TOKEN_GIFTER'], agent_roles['ALICE'], 1024)
    eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    a = r['block_number']
    ab = a.to_bytes(4, 'big')
    block_filter.add(ab)

    bb = r['transaction_index'].to_bytes(4, 'big')
    cb = ab + bb
    tx_filter.add(cb)

    tx_hashes.append(strip_0x(tx_hash_hex))

    # external tx two
    Nonce.next(agent_roles['ALICE'], 'foo', session=init_database)
    init_database.commit()

    init_eth_tester.mine_blocks(13)
    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)
    c = ERC20(default_chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, o) = c.transfer(foo_token, agent_roles['ALICE'], agent_roles['BOB'], 256)
    eth_rpc.do(o)
    o = receipt(tx_hash_hex)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    a = r['block_number']
    ab = a.to_bytes(4, 'big')
    block_filter.add(ab)

    bb = r['transaction_index'].to_bytes(4, 'big')
    cb = ab + bb
    tx_filter.add(cb)

    tx_hashes.append(strip_0x(tx_hash_hex))

    init_eth_tester.mine_blocks(28)

    # custodial tx 1
    api = Api(str(default_chain_spec), queue=None)
    t = api.transfer(agent_roles['ALICE'], agent_roles['CAROL'], 64, 'FOO')
    r = t.get_leaf()
    assert t.successful()
    tx_hashes.append(r)

    # custodial tx 2
    api = Api(str(default_chain_spec), queue=None)
    t = api.transfer(agent_roles['ALICE'], agent_roles['DAVE'], 16, 'FOO')
    r = t.get_leaf()
    assert t.successful()
    tx_hashes.append(r)

    logg.debug('r {}'.format(r))

    # test the api
    t = api.list(agent_roles['ALICE'], external_task='cic_eth.pytest.mock.filter.filter')
    r = t.get_leaf()
    assert t.successful()

    assert len(r) == 3
    logg.debug('rrrr {}'.format(r))

    logg.debug('testing against hashes {}'.format(tx_hashes))
    for tx in r:
        logg.debug('have tx {}'.format(tx))
        tx_hashes.remove(strip_0x(tx['hash']))
    assert len(tx_hashes) == 1
