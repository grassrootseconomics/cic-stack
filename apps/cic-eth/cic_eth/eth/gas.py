# standard imports
import logging

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

    def __init__(self, w3):
        self.w3 = w3
        self.gas_price_current = w3.eth.gas_price()


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
