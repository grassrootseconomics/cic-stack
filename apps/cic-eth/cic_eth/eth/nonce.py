# local imports
from cic_eth.db.models.nonce import Nonce

class NonceOracle():
    """Ensures atomic nonce increments for all transactions across all tasks and threads.

    :param address: Address to generate nonces for
    :type address: str, 0x-hex
    :param default_nonce: Initial nonce value to use if no nonce cache entry already exists
    :type default_nonce: number
    """
    def __init__(self, address, default_nonce):
        self.address = address
        self.default_nonce = default_nonce


    def next(self, session=None):
        """Get next unique nonce.

        :returns: Nonce
        :rtype: number
        """
        return Nonce.next(self.address, self.default_nonce, session=session)
