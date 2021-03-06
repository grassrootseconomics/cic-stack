# standard imports
import decimal
import logging
from datetime import datetime

# third-party imports
from cic_eth.api import Api

# local imports
from cic_ussd.balance import get_cached_operational_balance
from cic_ussd.notifications import Notifier


logg = logging.getLogger()
notifier = Notifier()


def truncate(value: float, decimals: int):
    """This function truncates a value to a specified number of decimals places.
    :param value: The value to be truncated.
    :type value: float
    :param decimals: The number of decimals for the value to be truncated to
    :type decimals: int
    :return: The truncated value.
    :rtype: int
    """
    decimal.getcontext().rounding = decimal.ROUND_DOWN
    contextualized_value = decimal.Decimal(value)
    return round(contextualized_value, decimals)


def from_wei(value: int) -> float:
    """This function converts values in Wei to a token in the cic network.
    :param value: Value in Wei
    :type value: int
    :return: SRF equivalent of value in Wei
    :rtype: float
    """
    value = float(value) / 1e+6
    return truncate(value=value, decimals=2)


def to_wei(value: int) -> int:
    """This functions converts values from a token in the cic network to Wei.
    :param value: Value in SRF
    :type value: int
    :return: Wei equivalent of value in SRF
    :rtype: int
    """
    return int(value * 1e+18)


class IncomingTransactionProcessor:

    def __init__(self, phone_number: str, preferred_language: str, token_symbol: str, value: int):
        """
        :param phone_number: The recipient's phone number.
        :type phone_number: str
        :param preferred_language: The user's preferred language.
        :type preferred_language: str
        :param token_symbol: The symbol for the token the recipient receives.
        :type token_symbol: str
        :param value: The amount of tokens received in the transactions.
        :type value: int
        """
        self.phone_number = phone_number
        self.preferred_language = preferred_language
        self.token_symbol = token_symbol
        self.value = value

    def process_token_gift_incoming_transactions(self):
        """This function processes incoming transactions with a "tokengift" param, it collects all appropriate data to
        send out notifications to users when their accounts are successfully created.

        """
        balance = from_wei(value=self.value)
        key = 'sms.account_successfully_created'
        notifier.send_sms_notification(key=key,
                                       phone_number=self.phone_number,
                                       preferred_language=self.preferred_language,
                                       balance=balance,
                                       token_symbol=self.token_symbol)

    def process_transfer_incoming_transaction(self, sender_information: str, recipient_blockchain_address: str):
        """This function processes incoming transactions with the "transfer" param and issues notifications to users
        about reception of funds into their accounts.
        :param sender_information: A string with a user's full name and phone number.
        :type sender_information: str
        :param recipient_blockchain_address:
        type recipient_blockchain_address: str
        """
        key = 'sms.received_tokens'
        amount = from_wei(value=self.value)
        timestamp = datetime.now().strftime('%d-%m-%y, %H:%M %p')

        operational_balance = get_cached_operational_balance(blockchain_address=recipient_blockchain_address)

        notifier.send_sms_notification(key=key,
                                       phone_number=self.phone_number,
                                       preferred_language=self.preferred_language,
                                       amount=amount,
                                       token_symbol=self.token_symbol,
                                       tx_sender_information=sender_information,
                                       timestamp=timestamp,
                                       balance=operational_balance)


class OutgoingTransactionProcessor:

    def __init__(self, chain_str: str, from_address: str, to_address: str):
        """
        :param chain_str: The chain name and network id.
        :type chain_str: str
        :param from_address: Ethereum address of the sender
        :type from_address: str, 0x-hex
        :param to_address: Ethereum address of the recipient
        :type to_address: str, 0x-hex
        """
        self.cic_eth_api = Api(chain_str=chain_str)
        self.from_address = from_address
        self.to_address = to_address

    def process_outgoing_transfer_transaction(self, amount: int, token_symbol='SRF'):
        """This function initiates standard transfers between one account to another
        :param amount: The amount of tokens to be sent
        :type amount: int
        :param token_symbol: ERC20 token symbol of token to send
        :type token_symbol: str
        """
        self.cic_eth_api.transfer(from_address=self.from_address,
                                  to_address=self.to_address,
                                  value=to_wei(value=amount),
                                  token_symbol=token_symbol)
