# local imports
from cic_eth.check.gas import health
from cic_eth.db.models.role import AccountRole

def test_check_gas(
    config,
    init_database,
    default_chain_spec,
    eth_rpc,
    custodial_roles,
    whoever,
        ):

    config.add(str(default_chain_spec), 'CIC_CHAIN_SPEC', exists_ok=True)
    config.add(100, 'ETH_GAS_GIFTER_MINIMUM_BALANCE', exists_ok=True)
    assert health(config=config)

    AccountRole.set('GAS_GIFTER', whoever, session=init_database)
    init_database.commit()
    assert not health(config=config)
