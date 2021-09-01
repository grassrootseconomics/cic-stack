# standard import
import decimal
import json
import logging
from typing import Dict, Tuple

# external import
from cic_eth.api import Api
from sqlalchemy.orm.session import Session

# local import
from cic_ussd.account.chain import Chain
from cic_ussd.account.tokens import get_cached_default_token
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase
from cic_ussd.error import UnknownUssdRecipient
from cic_ussd.translation import translation_for

logg = logging.getLogger(__name__)


def _add_tags(action_tag_key: str, preferred_language: str, direction_tag_key: str, transaction: dict):
    """ This function adds action and direction tags to a transaction data object.
    :param action_tag_key: Key mapping to a helper entry in the translation files describing an action.
    :type action_tag_key: str
    :param preferred_language: An account's set preferred language.
    :type preferred_language: str
    :param direction_tag_key: Key mapping to a helper entry in the translation files describing a transaction's
    direction relative to the transaction's subject account.
    :type direction_tag_key: str
    :param transaction: Parsed transaction data object.
    :type transaction: dict
    """
    action_tag = translation_for(action_tag_key, preferred_language)
    direction_tag = translation_for(direction_tag_key, preferred_language)
    transaction['action_tag'] = action_tag
    transaction['direction_tag'] = direction_tag


def aux_transaction_data(preferred_language: str, transaction: dict) -> dict:
    """This function adds auxiliary data to a transaction object offering contextual information relative to the
    subject account's role in the transaction.
    :param preferred_language: An account's set preferred language.
    :type preferred_language: str
    :param transaction: Parsed transaction data object.
    :type transaction: dict
    :return: Transaction object with contextual data.
    :rtype: dict
    """
    role = transaction.get('role')
    if role == 'recipient':
        _add_tags('helpers.received', preferred_language, 'helpers.from', transaction)
    if role == 'sender':
        _add_tags('helpers.sent', preferred_language, 'helpers.to', transaction)
    return transaction


def from_wei(value: int) -> float:
    """This function converts values in Wei to a token in the cic network.
    :param value: Value in Wei
    :type value: int
    :return: SRF equivalent of value in Wei
    :rtype: float
    """
    cached_token_data = json.loads(get_cached_default_token(Chain.spec.__str__()))
    token_decimals: int = cached_token_data.get('decimals')
    value = float(value) / (10**token_decimals)
    return truncate(value=value, decimals=2)


def to_wei(value: int) -> int:
    """This functions converts values from a token in the cic network to Wei.
    :param value: Value in SRF
    :type value: int
    :return: Wei equivalent of value in SRF
    :rtype: int
    """
    cached_token_data = json.loads(get_cached_default_token(Chain.spec.__str__()))
    token_decimals: int = cached_token_data.get('decimals')
    return int(value * (10**token_decimals))


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


def transaction_actors(transaction: dict) -> Tuple[Dict, Dict]:
    """ This function parses transaction data into a tuple of transaction data objects representative of
    of the source and destination account's involved in a transaction.
    :param transaction: Transaction data object.
    :type transaction: dict
    :return: Recipient and sender transaction data object
    :rtype: Tuple[Dict, Dict]
    """
    destination_token_symbol = transaction.get('destination_token_symbol')
    destination_token_value = transaction.get('destination_token_value') or transaction.get('to_value')
    recipient_blockchain_address = transaction.get('recipient')
    sender_blockchain_address = transaction.get('sender')
    source_token_symbol = transaction.get('source_token_symbol')
    source_token_value = transaction.get('source_token_value') or transaction.get('from_value')

    recipient_transaction_data = {
        "token_symbol": destination_token_symbol,
        "token_value": destination_token_value,
        "blockchain_address": recipient_blockchain_address,
        "role": "recipient",
    }
    sender_transaction_data = {
        "blockchain_address": sender_blockchain_address,
        "token_symbol": source_token_symbol,
        "token_value": source_token_value,
        "role": "sender",
    }
    return recipient_transaction_data, sender_transaction_data


def validate_transaction_account(blockchain_address: str, role: str, session: Session) -> Account:
    """This function checks whether the blockchain address specified in a parsed transaction object resolves to an
    account object in the ussd system.
    :param blockchain_address:
    :type blockchain_address:
    :param role:
    :type role:
    :param session:
    :type session:
    :return:
    :rtype:
    """
    session = SessionBase.bind_session(session)
    account = session.query(Account).filter_by(blockchain_address=blockchain_address).first()
    if not account:
        if role == 'recipient':
            raise UnknownUssdRecipient(
                f'Tx for recipient: {blockchain_address} has no matching account in the system.'
            )
        if role == 'sender':
            logg.warning(f'Tx from sender: {blockchain_address} has no matching account in system.')

    SessionBase.release_session(session)
    return account


class OutgoingTransaction:

    def __init__(self, chain_str: str, from_address: str, to_address: str):
        """
        :param chain_str: The chain name and network id.
        :type chain_str: str
        :param from_address: Ethereum address of the sender
        :type from_address: str, 0x-hex
        :param to_address: Ethereum address of the recipient
        :type to_address: str, 0x-hex
        """
        self.chain_str = chain_str
        self.cic_eth_api = Api(chain_str=chain_str)
        self.from_address = from_address
        self.to_address = to_address

    def transfer(self, amount: int, token_symbol: str):
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
