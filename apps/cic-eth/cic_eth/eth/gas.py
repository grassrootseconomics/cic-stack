# standard imports
import logging

# external imports
import celery
from chainlib.eth.gas import price
from hexathon import strip_0x

# local imports
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.base import SessionBase

logg = logging.getLogger()


class GasOracle():
    """Provides gas pricing for transactions.

    :param w3: Web3 object
    :type w3: web3.Web3
    """

    __safe_threshold_amount_value = 2000000000 * 60000 * 3
    __refill_amount_value = __safe_threshold_amount_value * 5
    default_gas_limit = 21000

    def __init__(self, conn):
        o = price()
        r = conn.do(o)
        b = bytes.from_hex(strip_0x(r))
        self.gas_price_current = int.from_bytes(b, 'big')

        #self.w3 = w3
        #self.gas_price_current = w3.eth.gas_price()


    def safe_threshold_amount(self):
        """The gas balance threshold under which a new gas refill transaction should be initiated.

        :returns: Gas token amount
        :rtype: number
        """
        g = GasOracle.__safe_threshold_amount_value
        logg.warning('gas safe threshold is currently hardcoded to {}'.format(g))
        return g


    def refill_amount(self):
        """The amount of gas tokens to send in a gas refill transaction.

        :returns: Gas token amount
        :rtype: number
        """
        g = GasOracle.__refill_amount_value
        logg.warning('gas refill amount is currently hardcoded to {}'.format(g))
        return g

 
    def gas_provider(self):
        """Gas provider address.

        :returns: Etheerum account address
        :rtype: str, 0x-hex
        """
        session = SessionBase.create_session()
        a = AccountRole.get_address('GAS_GIFTER', session)
        logg.debug('gasgifter {}'.format(a))
        session.close()
        return a


    def gas_price(self, category='safe'):
        """Get projected gas price to use for a transaction at the current moment.

        When the category parameter is implemented, it can be used to control the priority of a transaction in the network.

        :param category: Bid level category to return price for. Currently has no effect.
        :type category: str 
        :returns: Gas price
        :rtype: number
        """
        #logg.warning('gas price hardcoded to category "safe"')
        #g = 100
        #return g
        return self.gas_price_current


def create_check_gas_task(tx_signed_raws_hex, chain_spec, holder_address, gas=None, tx_hashes_hex=None, queue=None):
    """Creates a celery task signature for a check_gas task that adds the task to the outgoing queue to be processed by the dispatcher.

    If tx_hashes_hex is not spefified, a preceding task chained to check_gas must supply the transaction hashes as its return value.

    :param tx_signed_raws_hex: Raw signed transaction data
    :type tx_signed_raws_hex: list of str, 0x-hex
    :param chain_spec: Chain spec of address to add check gas for
    :type chain_spec: chainlib.chain.ChainSpec
    :param holder_address: Address sending the transactions
    :type holder_address: str, 0x-hex
    :param gas: Gas budget hint for transactions
    :type gas: int
    :param tx_hashes_hex: Transaction hashes
    :type tx_hashes_hex: list of str, 0x-hex
    :param queue: Task queue
    :type queue: str
    :returns: Signature of task chain
    :rtype: celery.Signature
    """
    s_check_gas = None
    if tx_hashes_hex != None:
        s_check_gas = celery.signature(
                'cic_eth.eth.tx.check_gas',
                [
                    tx_hashes_hex,
                    chain_spec.asdict(),
                    tx_signed_raws_hex,
                    holder_address,
                    gas,
                    ],
                queue=queue,
                )
    else:
        s_check_gas = celery.signature(
                'cic_eth.eth.tx.check_gas',
                [
                    chain_spec.asdict(),
                    tx_signed_raws_hex,
                    holder_address,
                    gas,
                    ],
                queue=queue,
                )
    return s_check_gas
