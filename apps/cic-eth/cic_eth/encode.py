# external imports
from chainlib.eth.constant import ZERO_ADDRESS
from chainqueue.encode import TxHexNormalizer
from chainlib.eth.tx import unpack

tx_normalize = TxHexNormalizer()

ZERO_ADDRESS_NORMAL = tx_normalize.wallet_address(ZERO_ADDRESS)


def unpack_normal(signed_tx_bytes, chain_spec):
    tx = unpack(signed_tx_bytes, chain_spec)
    tx['hash'] = tx_normalize.tx_hash(tx['hash'])
    tx['from'] = tx_normalize.wallet_address(tx['from'])
    tx['to'] = tx_normalize.wallet_address(tx['to'])
    return tx
