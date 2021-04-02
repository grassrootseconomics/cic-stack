import os
import logging

import pytest

from cic_eth.db.models.convert import TxConvertTransfer
from cic_eth.db.error import UnknownConvertError

logg = logging.getLogger()


def test_convert_transfer(
        init_database,
        default_chain_spec,
        ):

    tx_hash_hex = '0x' + os.urandom(32).hex()
    recipient = '0x' + os.urandom(20).hex()
    txct = TxConvertTransfer(tx_hash_hex, recipient, str(default_chain_spec))
    init_database.add(txct)
    init_database.commit()

    txct = TxConvertTransfer.get(tx_hash_hex)
    
    assert txct.convert_tx_hash == tx_hash_hex

    tx_hash_bogus_hex = '0x' + os.urandom(32).hex()
    with pytest.raises(UnknownConvertError):
        TxConvertTransfer.get(tx_hash_bogus_hex)
