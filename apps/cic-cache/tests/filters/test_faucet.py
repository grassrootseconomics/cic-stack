# standard imports
import logging

# external imports
from chainlib.chain import ChainSpec
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.block import (
        block_by_hash,
        Block,
        )
from chainlib.eth.tx import (
        receipt,
        unpack,
        transaction,
        Tx,
        )
from hexathon import strip_0x
from erc20_faucet.faucet import SingleShotFaucet
from sqlalchemy import text

# local imports
from cic_cache.db import add_tag
from cic_cache.runnable.daemons.filters.faucet import FaucetFilter

logg = logging.getLogger()


def test_filter_faucet(
        eth_rpc,
        eth_signer,
        foo_token,
        faucet_noregistry,
        init_database,
        list_defaults,
        contract_roles,
        agent_roles,
        tags,
        ):

    chain_spec = ChainSpec('foo', 'bar', 42, 'baz')

    fltr = FaucetFilter(chain_spec, contract_roles['CONTRACT_DEPLOYER'])

    add_tag(init_database, fltr.tag_name, domain=fltr.tag_domain)

    nonce_oracle = RPCNonceOracle(agent_roles['ALICE'], eth_rpc)
    c = SingleShotFaucet(chain_spec, signer=eth_signer, nonce_oracle=nonce_oracle)
    (tx_hash_hex, o) = c.give_to(faucet_noregistry, agent_roles['ALICE'], agent_roles['ALICE'])
    r = eth_rpc.do(o)

    tx_src = unpack(bytes.fromhex(strip_0x(o['params'][0])), chain_spec)

    o = receipt(r)
    r = eth_rpc.do(o)
    rcpt = Tx.src_normalize(r)

    assert r['status'] == 1

    o = block_by_hash(r['block_hash'])
    r = eth_rpc.do(o)
    block_object = Block(r)

    tx = Tx(tx_src, block_object)
    tx.apply_receipt(rcpt)

    r = fltr.filter(eth_rpc, block_object, tx, init_database)
    assert r

    s = text("SELECT x.tx_hash FROM tag a INNER JOIN tag_tx_link l ON l.tag_id = a.id INNER JOIN tx x ON x.id = l.tx_id WHERE a.domain = :a AND a.value = :b")
    r = init_database.execute(s, {'a': fltr.tag_domain, 'b': fltr.tag_name}).fetchone()
    assert r[0] == tx.hash
