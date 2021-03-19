# external imports
import celery
from chainlib.eth.erc20 import ERC20
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.eth.tx import receipt


def test_erc20_balance(
        default_chain_spec,
        foo_token,
        token_roles,
        agent_roles,
        eth_signer,
        eth_rpc,
        celery_worker,
        ):

    nonce_oracle = RPCNonceOracle(token_roles['FOO_TOKEN_OWNER'], eth_rpc)
    c = ERC20(signer=eth_signer, nonce_oracle=nonce_oracle)
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

