# standard imports
import logging
from collections import deque

# third-party imports
from cic_eth.api import Api

# local imports
from cic_ussd.transactions import from_wei

logg = logging.getLogger()


class BalanceManager:

    def __init__(self, address: str, chain_str: str, token_symbol: str):
        """
        :param address: Ethereum address of account whose balance is being queried
        :type address: str, 0x-hex
        :param chain_str: The chain name and network id.
        :type chain_str: str
        :param token_symbol: ERC20 token symbol of whose balance is being queried
        :type token_symbol: str
        """
        self.address = address
        self.chain_str = chain_str
        self.token_symbol = token_symbol

    def get_operational_balance(self) -> float:
        """This question queries cic-eth for an account's balance
        :return: The current balance of the account as reflected on the blockchain.
        :rtype: int
        """
        cic_eth_api = Api(chain_str=self.chain_str, callback_task=None)
        balance_request_task = cic_eth_api.balance(address=self.address, token_symbol=self.token_symbol)
        balance_request_task_results = balance_request_task.collect()
        balance_result = deque(balance_request_task_results, maxlen=1).pop()
        balance = from_wei(value=balance_result[-1])
        return balance
