# standard imports
import json
import logging

# external imports
import i18n.config
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.account.balance import calculate_available_balance, get_balances, get_cached_available_balance
from cic_ussd.account.chain import Chain
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.account.statement import (
    get_cached_statement,
    parse_statement_transactions,
    query_statement,
    statement_transaction_set
)
from cic_ussd.account.transaction import from_wei, to_wei
from cic_ussd.account.tokens import get_default_token_symbol
from cic_ussd.cache import cache_data_key, cache_data
from cic_ussd.db.models.account import Account
from cic_ussd.metadata import PersonMetadata
from cic_ussd.phone_number import Support
from cic_ussd.processor.util import latest_input, parse_person_metadata
from cic_ussd.translation import translation_for

logg = logging.getLogger(__name__)


class MenuProcessor:
    def __init__(self, account: Account, display_key: str, menu_name: str, session: Session, ussd_session: dict):
        self.account = account
        self.display_key = display_key
        self.identifier = bytes.fromhex(self.account.blockchain_address[2:])
        self.menu_name = menu_name
        self.session = session
        self.ussd_session = ussd_session

    def account_balances(self) -> str:
        """
        :return:
        :rtype:
        """
        available_balance = get_cached_available_balance(self.account.blockchain_address)
        logg.debug('Requires call to retrieve tax and bonus amounts')
        tax = ''
        bonus = ''
        token_symbol = get_default_token_symbol()
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(
            key=self.display_key,
            preferred_language=preferred_language,
            available_balance=available_balance,
            tax=tax,
            bonus=bonus,
            token_symbol=token_symbol
        )

    def account_statement(self) -> str:
        """
        :return:
        :rtype:
        """
        cached_statement = get_cached_statement(self.account.blockchain_address)
        statement = json.loads(cached_statement)
        statement_transactions = parse_statement_transactions(statement)
        transaction_sets = [statement_transactions[tx:tx+3] for tx in range(0, len(statement_transactions), 3)]
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        first_transaction_set = []
        middle_transaction_set = []
        last_transaction_set = []
        if transaction_sets:
            first_transaction_set = statement_transaction_set(preferred_language, transaction_sets[0])
        if len(transaction_sets) >= 2:
            middle_transaction_set = statement_transaction_set(preferred_language, transaction_sets[1])
        if len(transaction_sets) >= 3:
            last_transaction_set = statement_transaction_set(preferred_language, transaction_sets[2])
        if self.display_key == 'ussd.kenya.first_transaction_set':
            return translation_for(
                self.display_key, preferred_language, first_transaction_set=first_transaction_set
            )
        if self.display_key == 'ussd.kenya.middle_transaction_set':
            return translation_for(
                self.display_key, preferred_language, middle_transaction_set=middle_transaction_set
            )
        if self.display_key == 'ussd.kenya.last_transaction_set':
            return translation_for(
                self.display_key, preferred_language, last_transaction_set=last_transaction_set
            )

    def help(self):
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(self.display_key, preferred_language, support_phone=Support.phone_number)

    def person_metadata(self) -> str:
        """
        :return:
        :rtype:
        """
        person_metadata = PersonMetadata(self.identifier)
        cached_person_metadata = person_metadata.get_cached_metadata()
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        if cached_person_metadata:
            return parse_person_metadata(cached_person_metadata, self.display_key, preferred_language)
        absent = translation_for('helpers.not_provided', preferred_language)
        return translation_for(
            self.display_key,
            preferred_language,
            full_name=absent,
            gender=absent,
            age=absent,
            location=absent,
            products=absent
        )

    def pin_authorization(self, **kwargs) -> str:
        """
        :param kwargs:
        :type kwargs:
        :return:
        :rtype:
        """
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        if self.account.failed_pin_attempts == 0:
            return translation_for(f'{self.display_key}.first', preferred_language, **kwargs)

        remaining_attempts = 3
        remaining_attempts -= self.account.failed_pin_attempts
        retry_pin_entry = translation_for(
            'ussd.kenya.retry_pin_entry', preferred_language, remaining_attempts=remaining_attempts
        )
        return translation_for(
            f'{self.display_key}.retry', preferred_language, retry_pin_entry=retry_pin_entry
        )

    def start_menu(self):
        """
        :return:
        :rtype:
        """
        token_symbol = get_default_token_symbol()
        blockchain_address = self.account.blockchain_address
        balances = get_balances(blockchain_address, Chain.spec.__str__(), token_symbol, False)[0]
        key = cache_data_key(self.identifier, ':cic.balances')
        cache_data(key, json.dumps(balances))
        available_balance = calculate_available_balance(balances)

        query_statement(blockchain_address)

        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(
            self.display_key, preferred_language, account_balance=available_balance, account_token_name=token_symbol
        )

    def transaction_pin_authorization(self) -> str:
        """
        :return:
        :rtype:
        """
        recipient_phone_number = self.ussd_session.get('data').get('recipient_phone_number')
        recipient = Account.get_by_phone_number(recipient_phone_number, self.session)
        tx_recipient_information = recipient.standard_metadata_id()
        tx_sender_information = self.account.standard_metadata_id()
        token_symbol = get_default_token_symbol()
        user_input = self.ussd_session.get('data').get('transaction_amount')
        transaction_amount = to_wei(value=int(user_input))
        return self.pin_authorization(
            recipient_information=tx_recipient_information,
            transaction_amount=from_wei(transaction_amount),
            token_symbol=token_symbol,
            sender_information=tx_sender_information
        )

    def exit_insufficient_balance(self):
        """
        :return:
        :rtype:
        """
        available_balance = get_cached_available_balance(self.account.blockchain_address)
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        session_data = self.ussd_session.get('data')
        transaction_amount = session_data.get('transaction_amount')
        transaction_amount = to_wei(value=int(transaction_amount))
        token_symbol = get_default_token_symbol()
        recipient_phone_number = self.ussd_session.get('data').get('recipient_phone_number')
        recipient = Account.get_by_phone_number(recipient_phone_number, self.session)
        tx_recipient_information = recipient.standard_metadata_id()
        return translation_for(
            self.display_key,
            preferred_language,
            amount=from_wei(transaction_amount),
            token_symbol=token_symbol,
            recipient_information=tx_recipient_information,
            token_balance=available_balance
        )

    def exit_invalid_menu_option(self):
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(self.display_key, preferred_language, support_phone=Support.phone_number)

    def exit_pin_blocked(self):
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for('ussd.kenya.exit_pin_blocked', preferred_language, support_phone=Support.phone_number)

    def exit_successful_transaction(self):
        """
        :return:
        :rtype:
        """
        amount = int(self.ussd_session.get('data').get('transaction_amount'))
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        transaction_amount = to_wei(amount)
        token_symbol = get_default_token_symbol()
        recipient_phone_number = self.ussd_session.get('data').get('recipient_phone_number')
        recipient = Account.get_by_phone_number(phone_number=recipient_phone_number, session=self.session)
        tx_recipient_information = recipient.standard_metadata_id()
        tx_sender_information = self.account.standard_metadata_id()
        return translation_for(
            self.display_key,
            preferred_language,
            transaction_amount=from_wei(transaction_amount),
            token_symbol=token_symbol,
            recipient_information=tx_recipient_information,
            sender_information=tx_sender_information
        )


def response(account: Account, display_key: str, menu_name: str, session: Session, ussd_session: dict) -> str:
    """This function extracts the appropriate session data based on the current menu name. It then inserts them as
    keywords in the i18n function.
    :param account: The account in a running USSD session.
    :type account: Account
    :param display_key: The path in the translation files defining an appropriate ussd response
    :type display_key: str
    :param menu_name: The name by which a specific menu can be identified.
    :type menu_name: str
    :param session:
    :type session:
    :param ussd_session: A JSON serialized in-memory ussd session object
    :type ussd_session: dict
    :return: A string value corresponding the ussd menu's text value.
    :rtype: str
    """
    menu_processor = MenuProcessor(account, display_key, menu_name, session, ussd_session)

    if menu_name == 'start':
        return menu_processor.start_menu()

    if menu_name == 'help':
        return menu_processor.help()

    if menu_name == 'transaction_pin_authorization':
        return menu_processor.transaction_pin_authorization()

    if menu_name == 'exit_insufficient_balance':
        return menu_processor.exit_insufficient_balance()

    if menu_name == 'exit_successful_transaction':
        return menu_processor.exit_successful_transaction()

    if menu_name == 'account_balances':
        return menu_processor.account_balances()

    if 'pin_authorization' in menu_name:
        return menu_processor.pin_authorization()

    if 'enter_current_pin' in menu_name:
        return menu_processor.pin_authorization()

    if 'transaction_set' in menu_name:
        return menu_processor.account_statement()

    if menu_name == 'display_user_metadata':
        return menu_processor.person_metadata()

    if menu_name == 'exit_invalid_menu_option':
        return menu_processor.exit_invalid_menu_option()

    if menu_name == 'exit_pin_blocked':
        return menu_processor.exit_pin_blocked()

    preferred_language = get_cached_preferred_language(account.blockchain_address)

    return translation_for(display_key, preferred_language)
