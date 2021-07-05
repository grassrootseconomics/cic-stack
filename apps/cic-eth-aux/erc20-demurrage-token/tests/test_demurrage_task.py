# standard imports
import logging
import copy
import datetime

# external imports
import celery

# cic-eth imports
from cic_eth_aux.erc20_demurrage_token import (
        DemurrageCalculationTask,
        aux_setup,
        )

logg = logging.getLogger()


def test_demurrage_calulate_task(
        default_chain_spec,
        eth_rpc,
        cic_registry,
        celery_worker,
        register_demurrage_token,
        demurrage_token_symbol,
        contract_roles,
        load_config,
        ):
 
    config = copy.copy(load_config)
    config.add(str(default_chain_spec), 'CIC_CHAIN_SPEC', exists_ok=True)
    config.add(demurrage_token_symbol, 'CIC_DEFAULT_TOKEN_SYMBOL', exists_ok=True)
    aux_setup(eth_rpc, load_config, sender_address=contract_roles['CONTRACT_DEPLOYER'])

    since = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
    s = celery.signature(
            'cic_eth_aux.erc20_demurrage_token.get_adjusted_balance',
            [
                demurrage_token_symbol,
                1000,
                since.timestamp(),
                ],
            queue=None,
            )
    t = s.apply_async()
    r = t.get_leaf()
    assert t.successful()
    assert r == 980
