# local imports
from cic_eth.db.models.nonce import (
        Nonce,
        NonceReservation,
        )

class CustodialTaskNonceOracle():
    """Ensures atomic nonce increments for all transactions across all tasks and threads.

    :param address: Address to generate nonces for
    :type address: str, 0x-hex
    :param default_nonce: Initial nonce value to use if no nonce cache entry already exists
    :type default_nonce: number
    """
    def __init__(self, address, uuid, session=None):
        self.address = address
        self.uuid = uuid
        self.session = session


    def get_nonce(self):
        return self.next_nonce()


    def next_nonce(self):
        """Get next unique nonce.

        :returns: Nonce
        :rtype: number
        """
        return NonceReservation.release(self.address, self.uuid, session=self.session)
