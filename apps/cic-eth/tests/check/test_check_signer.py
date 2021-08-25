# local imports
from cic_eth.check.signer import health


def test_check_signer(
        default_chain_spec,
        config,
        eth_signer,
        eth_rpc,
        ):

    config.add(str(default_chain_spec), 'CHAIN_SPEC', exists_ok=True)
    assert health(config=config)
