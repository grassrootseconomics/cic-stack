import logging
import os

import celery

from cic_eth.db import TxConvertTransfer
from cic_eth.eth.bancor import BancorTxFactory

logg = logging.getLogger()


@pytest.mark.skip()
def test_transfer_after_convert(
        init_w3,
        init_database,
        cic_registry,
        bancor_tokens,
        bancor_registry,
        default_chain_spec,
        celery_session_worker,
        ):

    tx_hash = os.urandom(32).hex()
    txct = TxConvertTransfer(tx_hash, init_w3.eth.accounts[1], default_chain_spec)
    init_database.add(txct)
    init_database.commit()

    s = celery.signature(
            'cic_eth.eth.bancor.transfer_converted',
            [
                [
                    {
                        'address': bancor_tokens[0],
                    },
                ],
                init_w3.eth.accounts[0],
                init_w3.eth.accounts[1],
                1024,
                tx_hash,
                str(default_chain_spec),
            ],
        )
    t = s.apply_async()
    t.get()
    t.collect()
    assert t.successful()
