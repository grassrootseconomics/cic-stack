# standard imports
import json
import logging
from datetime import datetime, timedelta

# external imports
import i18n.config
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.account.balance import (calculate_available_balance,
                                      get_account_tokens_balance,
                                      get_adjusted_balance,
                                      get_balances,
                                      get_cached_adjusted_balance,
                                      get_cached_available_balance)
from cic_ussd.account.chain import Chain
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.account.statement import (
    get_cached_statement,
    parse_statement_transactions,
    query_statement)
from cic_ussd.account.tokens import (create_account_tokens_list,
                                     get_active_token_symbol,
                                     get_cached_token_data,
                                     get_cached_token_symbol_list,
                                     get_cached_token_data_list,
                                     parse_token_list)
from cic_ussd.account.transaction import from_wei, to_wei
from cic_ussd.cache import cache_data_key, cache_data, get_cached_data
from cic_ussd.db.models.account import Account
from cic_ussd.metadata import PersonMetadata
from cic_ussd.phone_number import Support
from cic_ussd.processor.poller import wait_for_session_data
from cic_ussd.processor.util import parse_person_metadata, ussd_menu_list
from cic_ussd.session.ussd_session import save_session_data
from cic_ussd.state_machine.logic.language import preferred_langauge_from_selection
from cic_ussd.translation import translation_for
from sqlalchemy.orm.session import Session

logg = logging.getLogger(__file__)


class MenuProcessor:
    def __init__(self, account: Account, display_key: str, menu_name: str, session: Session, ussd_session: dict):
        self.account = account
        self.display_key = display_key
        if account:
            self.identifier = bytes.fromhex(self.account.blockchain_address)
        self.menu_name = menu_name
        self.session = session
        self.ussd_session = ussd_session

    def account_balances(self) -> str:
        """
        :return:
        :rtype:
        """

        adjusted_balance = get_cached_adjusted_balance(self.identifier)
        token_symbol = get_active_token_symbol(self.account.blockchain_address)
        token_data = get_cached_token_data(self.account.blockchain_address, token_symbol)
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        with_available_balance = f'{self.display_key}.available_balance'
        with_fees = f'{self.display_key}.with_fees'
        decimals = token_data.get('decimals')
        available_balance = get_cached_available_balance(decimals, [self.identifier, token_symbol.encode('utf-8')])
        if not adjusted_balance:
            return translation_for(key=with_available_balance,
                                   preferred_language=preferred_language,
                                   available_balance=available_balance,
                                   token_symbol=token_symbol)

        adjusted_balance = json.loads(adjusted_balance)

        tax_wei = to_wei(decimals, int(available_balance)) - int(adjusted_balance)
        tax = from_wei(decimals, int(tax_wei))
        return translation_for(key=with_fees,
                               preferred_language=preferred_language,
                               available_balance=available_balance,
                               tax=tax,
                               token_symbol=token_symbol)

    def account_statement(self) -> str:
        """
        :return:
        :rtype:
        """
        cached_statement = get_cached_statement(self.account.blockchain_address)

        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')

        statement_list = []
        if cached_statement:
            statement_list = parse_statement_transactions(statement=json.loads(cached_statement))

        fallback = translation_for('helpers.no_transaction_history', preferred_language)
        transaction_sets = ussd_menu_list(fallback=fallback, menu_list=statement_list, split=3)

        if self.display_key == 'ussd.first_transaction_set':
            return translation_for(
                self.display_key, preferred_language, first_transaction_set=transaction_sets[0]
            )
        if self.display_key == 'ussd.middle_transaction_set':
            return translation_for(
                self.display_key, preferred_language, middle_transaction_set=transaction_sets[1]
            )
        if self.display_key == 'ussd.last_transaction_set':
            return translation_for(
                self.display_key, preferred_language, last_transaction_set=transaction_sets[2]
            )

    def add_guardian_pin_authorization(self):
        guardian_information = self.guardian_metadata()
        return self.pin_authorization(guardian_information=guardian_information)

    def guardian_list(self):
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        set_guardians = self.account.get_guardians()[:3]
        if set_guardians:
            guardians_list = ''
            guardians_list_header = translation_for('helpers.guardians_list_header', preferred_language)
            for phone_number in set_guardians:
                guardian = Account.get_by_phone_number(phone_number, self.session)
                guardian_information = guardian.standard_metadata_id()
                guardians_list += f'{guardian_information}\n'
            guardians_list = guardians_list_header + '\n' + guardians_list
        else:
            guardians_list = translation_for('helpers.no_guardians_list', preferred_language)
        return translation_for(self.display_key, preferred_language, guardians_list=guardians_list)

    def account_tokens(self) -> str:
        cached_token_data_list = get_cached_token_data_list(self.account.blockchain_address)
        token_data_list = parse_token_list(cached_token_data_list)

        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')

        fallback = translation_for('helpers.no_tokens_list', preferred_language)
        token_list_sets = ussd_menu_list(fallback=fallback, menu_list=token_data_list, split=3)

        data = {
            'account_tokens_list': cached_token_data_list
        }
        save_session_data(data=data, queue='cic-ussd', session=self.session, ussd_session=self.ussd_session)

        if self.display_key == 'ussd.first_account_tokens_set':
            return translation_for(
                self.display_key, preferred_language, first_account_tokens_set=token_list_sets[0]
            )
        if self.display_key == 'ussd.middle_account_tokens_set':
            return translation_for(
                self.display_key, preferred_language, middle_account_tokens_set=token_list_sets[1]
            )
        if self.display_key == 'ussd.last_account_tokens_set':
            return translation_for(
                self.display_key, preferred_language, last_account_tokens_set=token_list_sets[2]
            )

    def help(self) -> str:
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
            'ussd.retry_pin_entry', preferred_language, remaining_attempts=remaining_attempts
        )
        return translation_for(
            f'{self.display_key}.retry', preferred_language, retry_pin_entry=retry_pin_entry
        )

    def guarded_account_metadata(self):
        guarded_account_phone_number = self.ussd_session.get('data').get('guarded_account_phone_number')
        guarded_account = Account.get_by_phone_number(guarded_account_phone_number, self.session)
        return guarded_account.standard_metadata_id()

    def guardian_metadata(self):
        guardian_phone_number = self.ussd_session.get('data').get('guardian_phone_number')
        guardian = Account.get_by_phone_number(guardian_phone_number, self.session)
        return guardian.standard_metadata_id()

    def language(self):
        key = cache_data_key('system:languages'.encode('utf-8'), MetadataPointer.NONE)
        cached_system_languages = get_cached_data(key)
        language_list: list = json.loads(cached_system_languages)

        if self.account:
            preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        else:
            preferred_language = i18n.config.get('fallback')

        fallback = translation_for('helpers.no_language_list', preferred_language)
        language_list_sets = ussd_menu_list(fallback=fallback, menu_list=language_list, split=3)

        if self.display_key in ['ussd.initial_language_selection', 'ussd.select_preferred_language']:
            return translation_for(
                self.display_key, preferred_language, first_language_set=language_list_sets[0]
            )

        if 'middle_language_set' in self.display_key:
            return translation_for(
                self.display_key, preferred_language, middle_language_set=language_list_sets[1]
            )

        if 'last_language_set' in self.display_key:
            return translation_for(
                self.display_key, preferred_language, last_language_set=language_list_sets[2]
            )

    def account_creation_prompt(self):
        preferred_language = preferred_langauge_from_selection(self.ussd_session.get('user_input'))
        return translation_for(self.display_key, preferred_language)

    def reset_guarded_pin_authorization(self):
        guarded_account_information = self.guarded_account_metadata()
        return self.pin_authorization(guarded_account_information=guarded_account_information)

    def start_menu(self):
        """
        :return:
        :rtype:
        """
        chain_str = Chain.spec.__str__()
        token_symbol = get_active_token_symbol(self.account.blockchain_address)
        token_data = get_cached_token_data(self.account.blockchain_address, token_symbol)
        decimals = token_data.get('decimals')
        blockchain_address = self.account.blockchain_address
        balances = get_balances(blockchain_address, chain_str, token_symbol, False)[0]
        key = cache_data_key([self.identifier, token_symbol.encode('utf-8')], MetadataPointer.BALANCES)
        cache_data(key, json.dumps(balances))
        available_balance = calculate_available_balance(balances, decimals)
        now = datetime.now()
        if (now - self.account.created).days >= 30:
            if available_balance <= 0:
                logg.info(f'Not retrieving adjusted balance, available balance: {available_balance} is insufficient.')
            else:
                timestamp = int((now - timedelta(30)).timestamp())
                adjusted_balance = get_adjusted_balance(to_wei(decimals, int(available_balance)), chain_str, timestamp, token_symbol)
                key = cache_data_key([self.identifier, token_symbol.encode('utf-8')], MetadataPointer.BALANCES_ADJUSTED)
                cache_data(key, json.dumps(adjusted_balance))

        query_statement(blockchain_address)
        token_symbols_list = get_cached_token_symbol_list(blockchain_address)
        get_account_tokens_balance(blockchain_address, chain_str, token_symbols_list)
        create_account_tokens_list(blockchain_address)
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(
            self.display_key, preferred_language, account_balance=available_balance, account_token_name=token_symbol
        )

    def token_selection_pin_authorization(self) -> str:
        """
        :return:
        :rtype:
        """
        selected_token = self.ussd_session.get('data').get('selected_token')
        token_name = selected_token.get('name')
        token_symbol = selected_token.get('symbol')
        token_issuer = selected_token.get('issuer')
        token_contact = selected_token.get('contact')
        token_location = selected_token.get('location')
        token_data = f'{token_name} ({token_symbol})\n{token_issuer}\n{token_contact}\n{token_location}\n'
        return self.pin_authorization(token_data=token_data)

    def transaction_pin_authorization(self) -> str:
        """
        :return:
        :rtype:
        """
        recipient_phone_number = self.ussd_session.get('data').get('recipient_phone_number')
        recipient = Account.get_by_phone_number(recipient_phone_number, self.session)
        tx_recipient_information = recipient.standard_metadata_id()
        tx_sender_information = self.account.standard_metadata_id()
        token_symbol = get_active_token_symbol(self.account.blockchain_address)
        token_data = get_cached_token_data(self.account.blockchain_address, token_symbol)
        user_input = self.ussd_session.get('data').get('transaction_amount')
        decimals = token_data.get('decimals')
        transaction_amount = to_wei(decimals=decimals, value=int(user_input))
        return self.pin_authorization(
            recipient_information=tx_recipient_information,
            transaction_amount=from_wei(decimals, transaction_amount),
            token_symbol=token_symbol,
            sender_information=tx_sender_information
        )

    def exit_guardian_addition_success(self) -> str:
        guardian_information = self.guardian_metadata()
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(self.display_key,
                               preferred_language,
                               guardian_information=guardian_information)

    def exit_guardian_removal_success(self):
        guardian_information = self.guardian_metadata()
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(self.display_key,
                               preferred_language,
                               guardian_information=guardian_information)

    def exit_invalid_guardian_addition(self):
        failure_reason = self.ussd_session.get('data').get('failure_reason')
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(self.display_key, preferred_language, error_exit=failure_reason)

    def exit_invalid_guardian_removal(self):
        failure_reason = self.ussd_session.get('data').get('failure_reason')
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(self.display_key, preferred_language, error_exit=failure_reason)

    def exit_pin_reset_initiated_success(self):
        guarded_account_information = self.guarded_account_metadata()
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(self.display_key,
                               preferred_language,
                               guarded_account_information=guarded_account_information)

    def exit_insufficient_balance(self):
        """
        :return:
        :rtype:
        """
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        session_data = self.ussd_session.get('data')
        token_symbol = get_active_token_symbol(self.account.blockchain_address)
        token_data = get_cached_token_data(self.account.blockchain_address, token_symbol)
        decimals = token_data.get('decimals')
        available_balance = get_cached_available_balance(decimals, [self.identifier, token_symbol.encode('utf-8')])
        transaction_amount = session_data.get('transaction_amount')
        transaction_amount = to_wei(decimals=decimals, value=int(transaction_amount))
        recipient_phone_number = self.ussd_session.get('data').get('recipient_phone_number')
        recipient = Account.get_by_phone_number(recipient_phone_number, self.session)
        tx_recipient_information = recipient.standard_metadata_id()
        return translation_for(
            self.display_key,
            preferred_language,
            amount=from_wei(decimals, transaction_amount),
            token_symbol=token_symbol,
            recipient_information=tx_recipient_information,
            token_balance=available_balance
        )

    def exit_invalid_menu_option(self):
        if self.account:
            preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        else:
            preferred_language = i18n.config.get('fallback')
        return translation_for(self.display_key, preferred_language, support_phone=Support.phone_number)

    def exit_pin_blocked(self):
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for('ussd.exit_pin_blocked', preferred_language, support_phone=Support.phone_number)

    def exit_successful_token_selection(self) -> str:
        selected_token = self.ussd_session.get('data').get('selected_token')
        token_symbol = selected_token.get('symbol')
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        return translation_for(self.display_key, preferred_language, token_symbol=token_symbol)

    def exit_successful_transaction(self):
        """
        :return:
        :rtype:
        """
        amount = int(self.ussd_session.get('data').get('transaction_amount'))
        preferred_language = get_cached_preferred_language(self.account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')
        token_symbol = get_active_token_symbol(self.account.blockchain_address)
        token_data = get_cached_token_data(self.account.blockchain_address, token_symbol)
        decimals = token_data.get('decimals')
        transaction_amount = to_wei(decimals, amount)
        recipient_phone_number = self.ussd_session.get('data').get('recipient_phone_number')
        recipient = Account.get_by_phone_number(phone_number=recipient_phone_number, session=self.session)
        tx_recipient_information = recipient.standard_metadata_id()
        tx_sender_information = self.account.standard_metadata_id()
        return translation_for(
            self.display_key,
            preferred_language,
            transaction_amount=from_wei(decimals, transaction_amount),
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

    if menu_name == 'account_creation_prompt':
        return menu_processor.account_creation_prompt()

    if menu_name == 'start':
        return menu_processor.start_menu()

    if menu_name == 'help':
        return menu_processor.help()

    if menu_name == 'transaction_pin_authorization':
        return menu_processor.transaction_pin_authorization()

    if menu_name == 'token_selection_pin_authorization':
        return menu_processor.token_selection_pin_authorization()

    if menu_name == 'exit_insufficient_balance':
        return menu_processor.exit_insufficient_balance()

    if menu_name == 'exit_invalid_guardian_addition':
        return menu_processor.exit_invalid_guardian_addition()

    if menu_name == 'exit_invalid_guardian_removal':
        return menu_processor.exit_invalid_guardian_removal()

    if menu_name == 'exit_successful_transaction':
        return menu_processor.exit_successful_transaction()

    if menu_name == 'exit_guardian_addition_success':
        return menu_processor.exit_guardian_addition_success()

    if menu_name == 'exit_guardian_removal_success':
        return menu_processor.exit_guardian_removal_success()

    if menu_name == 'exit_pin_reset_initiated_success':
        return menu_processor.exit_pin_reset_initiated_success()

    if menu_name == 'account_balances':
        return menu_processor.account_balances()

    if menu_name == 'guardian_list':
        return menu_processor.guardian_list()

    if menu_name == 'add_guardian_pin_authorization':
        return menu_processor.add_guardian_pin_authorization()

    if menu_name == 'reset_guarded_pin_authorization':
        return menu_processor.reset_guarded_pin_authorization()

    if 'pin_authorization' in menu_name:
        return menu_processor.pin_authorization()

    if 'enter_current_pin' in menu_name:
        return menu_processor.pin_authorization()

    if 'transaction_set' in menu_name:
        return menu_processor.account_statement()

    if 'account_tokens_set' in menu_name:
        return menu_processor.account_tokens()

    if 'language' in menu_name:
        return menu_processor.language()

    if menu_name == 'display_user_metadata':
        return menu_processor.person_metadata()

    if menu_name == 'exit_invalid_menu_option':
        return menu_processor.exit_invalid_menu_option()

    if menu_name == 'exit_pin_blocked':
        return menu_processor.exit_pin_blocked()

    if menu_name == 'exit_successful_token_selection':
        return menu_processor.exit_successful_token_selection()

    preferred_language = i18n.config.get('fallback')
    if account:
        preferred_language = get_cached_preferred_language(account.blockchain_address)

    return translation_for(display_key, preferred_language)
