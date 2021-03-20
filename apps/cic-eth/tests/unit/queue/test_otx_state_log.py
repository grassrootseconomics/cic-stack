# standard imports
import os

# local imports
from cic_eth.db.models.otx import Otx
from cic_eth.queue.tx import get_state_log


def test_otx_state_log(
        init_database,
        ):
  
    Otx.tracing = True

    address = '0x' + os.urandom(20).hex()
    tx_hash = '0x' + os.urandom(32).hex()
    signed_tx = '0x' + os.urandom(128).hex()
    otx = Otx.add(0, address, tx_hash, signed_tx, session=init_database)
    init_database.commit()

    log = get_state_log(tx_hash) 
    assert len(log) == 1
