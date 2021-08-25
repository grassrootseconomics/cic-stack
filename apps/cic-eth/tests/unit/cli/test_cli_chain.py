# external imports
import pytest
from chainlib.eth.gas import (
        Gas,
        RPCGasOracle,
        )
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.block import (
        block_latest,
        Block,
        )

# local imports
import cic_eth.cli


@pytest.mark.xfail()
def test_cli_rpc(
        eth_rpc,
        eth_signer,
        default_chain_spec,
        ):
    config = {
        'CHAIN_SPEC': str(default_chain_spec),
        'RPC_HTTP_PROVIDER': 'http://localhost:8545',
            }
    rpc = cic_eth.cli.RPC.from_config(config, default_label='foo') 
    conn = rpc.get_by_label('foo')
    #o = block_latest()
    #conn.do(o)


def test_cli_chain(
        default_chain_spec,
        eth_rpc,
        eth_signer,
        contract_roles,
        agent_roles,
        ):
    ifc = cic_eth.cli.EthChainInterface()

    nonce_oracle = RPCNonceOracle(contract_roles['CONTRACT_DEPLOYER'], conn=eth_rpc)
    gas_oracle = RPCGasOracle(conn=eth_rpc)
    c = Gas(default_chain_spec, nonce_oracle=nonce_oracle, gas_oracle=gas_oracle, signer=eth_signer)
    (tx_hash, o) = c.create(contract_roles['CONTRACT_DEPLOYER'], agent_roles['ALICE'], 1024)
    r = eth_rpc.do(o)

    o = ifc.tx_receipt(r)
    r = eth_rpc.do(o)
    assert r['status'] == 1

    o = ifc.block_by_number(1)
    block_src = eth_rpc.do(o)
    block = ifc.block_from_src(block_src)
    assert block.number == 1

    with pytest.raises(KeyError):
        assert block_src['gasUsed'] == 21000
        assert block_src['gas_used'] == 21000

    block_src = ifc.src_normalize(block_src)
    assert block_src['gasUsed'] == 21000
    assert block_src['gas_used'] == 21000

