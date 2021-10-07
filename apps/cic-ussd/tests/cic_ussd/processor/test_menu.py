# standard imports
import json
import datetime

# external imports
from chainlib.hash import strip_0x

# local imports
from cic_ussd.account.balance import get_cached_available_balance
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.account.statement import (
    get_cached_statement,
    parse_statement_transactions,
    statement_transaction_set
)
from cic_ussd.account.tokens import get_default_token_symbol
from cic_ussd.account.transaction import from_wei, to_wei
from cic_ussd.cache import cache_data, cache_data_key
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.metadata import PersonMetadata
from cic_ussd.phone_number import Support
from cic_ussd.processor.menu import response
from cic_ussd.processor.util import parse_person_metadata
from cic_ussd.translation import translation_for


# test imports


def test_menu_processor(activated_account,
                        balances,
                        cache_balances,
                        cache_default_token_data,
                        cache_preferences,
                        cache_person_metadata,
                        cache_statement,
                        celery_session_worker,
                        generic_ussd_session,
                        init_database,
                        load_chain_spec,
                        load_support_phone,
                        load_ussd_menu,
                        mock_get_adjusted_balance,
                        mock_sync_balance_api_query,
                        mock_transaction_list_query,
                        valid_recipient):
    preferred_language = get_cached_preferred_language(activated_account.blockchain_address)
    available_balance = get_cached_available_balance(activated_account.blockchain_address)
    token_symbol = get_default_token_symbol()
    with_available_balance = 'ussd.kenya.account_balances.available_balance'
    with_fees = 'ussd.kenya.account_balances.with_fees'
    ussd_menu = UssdMenu.find_by_name('account_balances')
    name = ussd_menu.get('name')
    resp = response(activated_account, 'ussd.kenya.account_balances', name, init_database, generic_ussd_session)
    assert resp == translation_for(with_available_balance,
                                   preferred_language,
                                   available_balance=available_balance,
                                   token_symbol=token_symbol)

    identifier = bytes.fromhex(activated_account.blockchain_address)
    key = cache_data_key(identifier, ':cic.adjusted_balance')
    adjusted_balance = 45931650.64654012
    cache_data(key, json.dumps(adjusted_balance))
    resp = response(activated_account, 'ussd.kenya.account_balances', name, init_database, generic_ussd_session)
    tax_wei = to_wei(int(available_balance)) - int(adjusted_balance)
    tax = from_wei(int(tax_wei))
    assert resp == translation_for(key=with_fees,
                                   preferred_language=preferred_language,
                                   available_balance=available_balance,
                                   tax=tax,
                                   token_symbol=token_symbol)

    cached_statement = get_cached_statement(activated_account.blockchain_address)
    statement = json.loads(cached_statement)
    statement_transactions = parse_statement_transactions(statement)
    transaction_sets = [statement_transactions[tx:tx + 3] for tx in range(0, len(statement_transactions), 3)]
    first_transaction_set = []
    middle_transaction_set = []
    last_transaction_set = []
    if transaction_sets:
        first_transaction_set = statement_transaction_set(preferred_language, transaction_sets[0])
    if len(transaction_sets) >= 2:
        middle_transaction_set = statement_transaction_set(preferred_language, transaction_sets[1])
    if len(transaction_sets) >= 3:
        last_transaction_set = statement_transaction_set(preferred_language, transaction_sets[2])

    display_key = 'ussd.kenya.first_transaction_set'
    ussd_menu = UssdMenu.find_by_name('first_transaction_set')
    name = ussd_menu.get('name')
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)

    assert resp == translation_for(display_key, preferred_language, first_transaction_set=first_transaction_set)

    display_key = 'ussd.kenya.middle_transaction_set'
    ussd_menu = UssdMenu.find_by_name('middle_transaction_set')
    name = ussd_menu.get('name')
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)

    assert resp == translation_for(display_key, preferred_language, middle_transaction_set=middle_transaction_set)

    display_key = 'ussd.kenya.last_transaction_set'
    ussd_menu = UssdMenu.find_by_name('last_transaction_set')
    name = ussd_menu.get('name')
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)

    assert resp == translation_for(display_key, preferred_language, last_transaction_set=last_transaction_set)

    display_key = 'ussd.kenya.display_user_metadata'
    ussd_menu = UssdMenu.find_by_name('display_user_metadata')
    name = ussd_menu.get('name')
    identifier = bytes.fromhex(activated_account.blockchain_address)
    person_metadata = PersonMetadata(identifier)
    cached_person_metadata = person_metadata.get_cached_metadata()
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)
    assert resp == parse_person_metadata(cached_person_metadata, display_key, preferred_language)

    display_key = 'ussd.kenya.account_balances_pin_authorization'
    ussd_menu = UssdMenu.find_by_name('account_balances_pin_authorization')
    name = ussd_menu.get('name')
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)
    assert resp == translation_for(f'{display_key}.first', preferred_language)

    activated_account.failed_pin_attempts = 1
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)
    retry_pin_entry = translation_for('ussd.kenya.retry_pin_entry', preferred_language, remaining_attempts=2)
    assert resp == translation_for(f'{display_key}.retry', preferred_language, retry_pin_entry=retry_pin_entry)
    activated_account.failed_pin_attempts = 0

    display_key = 'ussd.kenya.start'
    ussd_menu = UssdMenu.find_by_name('start')
    name = ussd_menu.get('name')
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)
    assert resp == translation_for(display_key,
                                   preferred_language,
                                   account_balance=available_balance,
                                   account_token_name=token_symbol)

    display_key = 'ussd.kenya.start'
    ussd_menu = UssdMenu.find_by_name('start')
    name = ussd_menu.get('name')
    older_timestamp = (activated_account.created - datetime.timedelta(days=35))
    activated_account.created = older_timestamp
    init_database.flush()
    response(activated_account, display_key, name, init_database, generic_ussd_session)
    assert mock_get_adjusted_balance['timestamp'] == int((datetime.datetime.now() - datetime.timedelta(days=30)).timestamp())

    display_key = 'ussd.kenya.transaction_pin_authorization'
    ussd_menu = UssdMenu.find_by_name('transaction_pin_authorization')
    name = ussd_menu.get('name')
    generic_ussd_session['data'] = {
        'recipient_phone_number': valid_recipient.phone_number,
        'transaction_amount': '15'
    }
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)
    user_input = generic_ussd_session.get('data').get('transaction_amount')
    transaction_amount = to_wei(value=int(user_input))
    tx_recipient_information = valid_recipient.standard_metadata_id()
    tx_sender_information = activated_account.standard_metadata_id()
    assert resp == translation_for(f'{display_key}.first',
                                   preferred_language,
                                   recipient_information=tx_recipient_information,
                                   transaction_amount=from_wei(transaction_amount),
                                   token_symbol=token_symbol,
                                   sender_information=tx_sender_information)

    display_key = 'ussd.kenya.exit_insufficient_balance'
    ussd_menu = UssdMenu.find_by_name('exit_insufficient_balance')
    name = ussd_menu.get('name')
    generic_ussd_session['data'] = {
        'recipient_phone_number': valid_recipient.phone_number,
        'transaction_amount': '85'
    }
    transaction_amount = generic_ussd_session.get('data').get('transaction_amount')
    transaction_amount = to_wei(value=int(transaction_amount))
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)
    assert resp == translation_for(display_key,
                                   preferred_language,
                                   amount=from_wei(transaction_amount),
                                   token_symbol=token_symbol,
                                   recipient_information=tx_recipient_information,
                                   token_balance=available_balance)

    display_key = 'ussd.kenya.exit_invalid_menu_option'
    ussd_menu = UssdMenu.find_by_name('exit_invalid_menu_option')
    name = ussd_menu.get('name')
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)
    assert resp == translation_for(display_key, preferred_language, support_phone=Support.phone_number)

    display_key = 'ussd.kenya.exit_successful_transaction'
    ussd_menu = UssdMenu.find_by_name('exit_successful_transaction')
    name = ussd_menu.get('name')
    generic_ussd_session['data'] = {
        'recipient_phone_number': valid_recipient.phone_number,
        'transaction_amount': '15'
    }
    transaction_amount = generic_ussd_session.get('data').get('transaction_amount')
    transaction_amount = to_wei(value=int(transaction_amount))
    resp = response(activated_account, display_key, name, init_database, generic_ussd_session)
    assert resp == translation_for(display_key,
                                   preferred_language,
                                   transaction_amount=from_wei(transaction_amount),
                                   token_symbol=token_symbol,
                                   recipient_information=tx_recipient_information,
                                   sender_information=tx_sender_information)
