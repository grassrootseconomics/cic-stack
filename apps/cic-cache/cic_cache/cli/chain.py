# external imports
from chainlib.eth.block import (
        block_by_number,
        Block,
        )
from chainlib.eth.tx import (
        receipt,
        Tx,
        )
from chainlib.interface import ChainInterface


class EthChainInterface(ChainInterface):
    
    def __init__(self):
        self._tx_receipt = receipt
        self._block_by_number = block_by_number
        self._block_from_src = Block.from_src
        self._src_normalize = Tx.src_normalize

chain_interface = EthChainInterface()
