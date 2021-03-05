# standard imports
import logging

# local imports
from cic_registry import CICRegistry
from cic_eth.eth.nonce import NonceOracle
from cic_eth.eth import RpcClient

logg = logging.getLogger(__name__)


class TxFactory:
    """Base class for transaction factory classes.

    :param from_address: Signer address to create transaction on behalf of
    :type from_address: str, 0x-hex
    :param rpc_client: RPC connection object to use to acquire account nonce if no record in nonce cache
    :type rpc_client: cic_eth.eth.rpc.RpcClient
    """

    gas_price = 100
    """Gas price, updated between batches"""


    def __init__(self, from_address, rpc_client):
        self.address = from_address

        self.default_nonce = rpc_client.w3.eth.getTransactionCount(from_address, 'pending')
        self.nonce_oracle = NonceOracle(from_address, self.default_nonce)

        TxFactory.gas_price = rpc_client.gas_price()
        logg.debug('txfactory instance address {} gas price'.format(self.address, self.gas_price))
        

    def next_nonce(self, uuid, session=None):
        """Returns the current reserved nonce value, and increments it for next transaction.

        :returns: Nonce
        :rtype: number
        """
        return self.nonce_oracle.next_by_task_uuid(uuid, session=session)
