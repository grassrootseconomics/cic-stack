# standard imports
import json
import os

# external imports
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.account.balance import get_cached_available_balance
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.account.statement import (
    get_cached_statement,
    parse_statement_transactions
)
from cic_ussd.account.tokens import (get_active_token_symbol,
                                     get_cached_token_data)
from cic_ussd.account.transaction import from_wei, to_wei
from cic_ussd.cache import cache_data, cache_data_key, get_cached_data
from cic_ussd.metadata import PersonMetadata
from cic_ussd.phone_number import Support
from cic_ussd.processor.menu import response, MenuProcessor
from cic_ussd.processor.util import parse_person_metadata, ussd_menu_list
from cic_ussd.translation import translation_for


# test imports

def test_account_balance(activated_account, cache_balances, cache_preferences, cache_token_data,
                         generic_ussd_session, init_database, set_active_token):
    """blockchain_address = activated_account.blockchain_address
    token_symbol = get_active_token_symbol(blockchain_address)
    token_data = get_cached_token_data(blockchain_address, token_symbol)
    preferred_language = get_cached_preferred_language(blockchain_address)
    decimals = token_data.get("decimals")
    identifier = bytes.fromhex(blockchain_address)
    balances_identifier = [identifier, token_symbol.encode('utf-8')]
    available_balance = get_cached_available_balance(decimals, balances_identifier)
    with_available_balance = 'ussd.account_balances.available_balance'
    resp = response(activated_account, with_available_balance, with_available_balance[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(with_available_balance,
                                   preferred_language,
                                   available_balance=available_balance,
                                   token_symbol=token_symbol)

    with_fees = 'ussd.account_balances.with_fees'
    key = cache_data_key(balances_identifier, MetadataPointer.BALANCES_ADJUSTED)
    adjusted_balance = 45931650.64654012
    cache_data(key, json.dumps(adjusted_balance))
    resp = response(activated_account, with_fees, with_fees[5:], init_database, generic_ussd_session)
    tax_wei = to_wei(decimals, int(available_balance)) - int(adjusted_balance)
    tax = from_wei(decimals, int(tax_wei))
    assert resp == translation_for(key=with_fees,
                                   preferred_language=preferred_language,
                                   available_balance=available_balance,
                                   tax=tax,
                                   token_symbol=token_symbol)"""
    pass


def test_account_statement(activated_account,
                           cache_preferences,
                           cache_statement,
                           generic_ussd_session,
                           init_database,
                           set_active_token,
                           set_locale_files):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    cached_statement = get_cached_statement(blockchain_address)
    statement_list = parse_statement_transactions(statement=json.loads(cached_statement))
    first_transaction_set = 'ussd.first_transaction_set'
    middle_transaction_set = 'ussd.middle_transaction_set'
    last_transaction_set = 'ussd.last_transaction_set'
    fallback = translation_for('helpers.no_transaction_history', preferred_language)
    transaction_sets = ussd_menu_list(fallback=fallback, menu_list=statement_list, split=3)
    resp = response(activated_account, first_transaction_set, first_transaction_set[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(first_transaction_set, preferred_language, first_transaction_set=transaction_sets[0])
    resp = response(activated_account, middle_transaction_set, middle_transaction_set[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(middle_transaction_set, preferred_language,
                                   middle_transaction_set=transaction_sets[1])
    resp = response(activated_account, last_transaction_set, last_transaction_set[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(last_transaction_set, preferred_language, last_transaction_set=transaction_sets[2])


def test_add_guardian_pin_authorization(activated_account,
                                        cache_preferences,
                                        guardian_account,
                                        generic_ussd_session,
                                        init_database):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    add_guardian_pin_authorization = 'ussd.add_guardian_pin_authorization'
    activated_account.add_guardian(guardian_account.phone_number)
    init_database.flush()
    generic_ussd_session['external_session_id'] = os.urandom(20).hex()
    generic_ussd_session['msisdn'] = guardian_account.phone_number
    generic_ussd_session['data'] = {'guardian_phone_number': guardian_account.phone_number}
    generic_ussd_session['state'] = 'add_guardian_pin_authorization'
    resp = response(activated_account,
                    add_guardian_pin_authorization,
                    add_guardian_pin_authorization[5:],
                    init_database,
                    generic_ussd_session)
    assert resp == translation_for(f'{add_guardian_pin_authorization}.first', preferred_language,
                                   guardian_information=guardian_account.standard_metadata_id())


def test_guardian_list(activated_account,
                       cache_preferences,
                       generic_ussd_session,
                       guardian_account,
                       init_database):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    guardians_list = 'ussd.guardian_list'
    guardians_list_header = translation_for('helpers.guardians_list_header', preferred_language)
    guardian_information = guardian_account.standard_metadata_id()
    guardians = guardians_list_header + '\n' + f'{guardian_information}\n'
    activated_account.add_guardian(guardian_account.phone_number)
    init_database.flush()
    resp = response(activated_account, guardians_list, guardians_list[5:], init_database, generic_ussd_session)
    assert resp == translation_for(guardians_list, preferred_language, guardians_list=guardians)
    guardians = translation_for('helpers.no_guardians_list', preferred_language)
    identifier = bytes.fromhex(guardian_account.blockchain_address)
    key = cache_data_key(identifier, MetadataPointer.PREFERENCES)
    cache_data(key, json.dumps({'preferred_language': preferred_language}))
    resp = response(guardian_account, guardians_list, guardians_list[5:], init_database, generic_ussd_session)
    assert resp == translation_for(guardians_list, preferred_language, guardians_list=guardians)


def test_account_tokens(activated_account, cache_token_data_list, celery_session_worker, generic_ussd_session,
                        init_cache, init_database):
    """blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    cached_token_data_list = get_cached_token_data_list(blockchain_address)
    token_data_list = ['1. GFT 50.0']
    fallback = translation_for('helpers.no_tokens_list', preferred_language)
    token_list_sets = ussd_menu_list(fallback=fallback, menu_list=token_data_list, split=3)
    first_account_tokens_set = 'ussd.first_account_tokens_set'
    middle_account_tokens_set = 'ussd.middle_account_tokens_set'
    last_account_tokens_set = 'ussd.last_account_tokens_set'
    resp = response(activated_account, first_account_tokens_set, first_account_tokens_set[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(first_account_tokens_set, preferred_language,
                                   first_account_tokens_set=token_list_sets[0])
    assert generic_ussd_session.get('data').get('account_tokens_list') == cached_token_data_list
    resp = response(activated_account, middle_account_tokens_set, middle_account_tokens_set[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(middle_account_tokens_set, preferred_language,
                                   middle_account_tokens_set=token_list_sets[1])
    resp = response(activated_account, last_account_tokens_set, last_account_tokens_set[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(last_account_tokens_set, preferred_language,
                                   last_account_tokens_set=token_list_sets[2])"""
    pass


def test_help(activated_account, cache_preferences, generic_ussd_session, init_database):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    help = 'ussd.help'
    resp = response(activated_account, help, help[5:], init_database, generic_ussd_session)
    assert resp == translation_for(help, preferred_language, support_phone=Support.phone_number)


def test_person_data(activated_account, cache_person_metadata, cache_preferences, cached_ussd_session,
                     generic_ussd_session, init_database):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    identifier = bytes.fromhex(blockchain_address)
    display_user_metadata = 'ussd.display_user_metadata'
    person_metadata = PersonMetadata(identifier)
    cached_person_metadata = person_metadata.get_cached_metadata()
    resp = response(activated_account, display_user_metadata, display_user_metadata[5:], init_database,
                    generic_ussd_session)
    assert resp == parse_person_metadata(cached_person_metadata, display_user_metadata, preferred_language)


def test_guarded_account_metadata(activated_account, generic_ussd_session, init_database):
    reset_guarded_pin_authorization = 'ussd.reset_guarded_pin_authorization'
    generic_ussd_session['data'] = {'guarded_account_phone_number': activated_account.phone_number}
    menu_processor = MenuProcessor(activated_account, reset_guarded_pin_authorization,
                                   reset_guarded_pin_authorization[5:], init_database, generic_ussd_session)
    assert menu_processor.guarded_account_metadata() == activated_account.standard_metadata_id()


def test_guardian_metadata(activated_account, generic_ussd_session, guardian_account, init_database):
    add_guardian_pin_authorization = 'ussd.add_guardian_pin_authorization'
    generic_ussd_session['data'] = {'guardian_phone_number': guardian_account.phone_number}
    menu_processor = MenuProcessor(activated_account, add_guardian_pin_authorization,
                                   add_guardian_pin_authorization[5:], init_database, generic_ussd_session)
    assert menu_processor.guardian_metadata() == guardian_account.standard_metadata_id()


def test_language(activated_account, cache_preferences, generic_ussd_session, init_database, load_languages):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    initial_language_selection = 'ussd.initial_language_selection'
    select_preferred_language = 'ussd.select_preferred_language'
    initial_middle_language_set = 'ussd.initial_middle_language_set'
    middle_language_set = 'ussd.middle_language_set'
    initial_last_language_set = 'ussd.initial_last_language_set'
    last_language_set = 'ussd.last_language_set'

    key = cache_data_key('system:languages'.encode('utf-8'), MetadataPointer.NONE)
    cached_system_languages = get_cached_data(key)
    language_list: list = json.loads(cached_system_languages)

    fallback = translation_for('helpers.no_language_list', preferred_language)
    language_list_sets = ussd_menu_list(fallback=fallback, menu_list=language_list, split=3)

    resp = response(activated_account, initial_language_selection, initial_language_selection[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(initial_language_selection, preferred_language,
                                   first_language_set=language_list_sets[0])

    resp = response(activated_account, select_preferred_language, select_preferred_language[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(select_preferred_language, preferred_language,
                                   first_language_set=language_list_sets[0])

    resp = response(activated_account, initial_middle_language_set, initial_middle_language_set[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(initial_middle_language_set, preferred_language,
                                   middle_language_set=language_list_sets[1])

    resp = response(activated_account, initial_last_language_set, initial_last_language_set[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(initial_last_language_set, preferred_language,
                                   last_language_set=language_list_sets[2])

    resp = response(activated_account, middle_language_set, middle_language_set[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(middle_language_set, preferred_language, middle_language_set=language_list_sets[1])

    resp = response(activated_account, last_language_set, last_language_set[5:], init_database, generic_ussd_session)
    assert resp == translation_for(last_language_set, preferred_language, last_language_set=language_list_sets[2])


def test_account_creation_prompt(activated_account, cache_preferences, generic_ussd_session, init_database,
                                 load_languages):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    user_input = ''
    if preferred_language == 'en':
        user_input = '1'
    elif preferred_language == 'sw':
        user_input = '2'
    account_creation_prompt = 'ussd.account_creation_prompt'
    generic_ussd_session['user_input'] = user_input
    resp = response(activated_account, account_creation_prompt, account_creation_prompt[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(account_creation_prompt, preferred_language)


def test_reset_guarded_pin_authorization(activated_account, cache_preferences, generic_ussd_session, guardian_account,
                                         init_database):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    reset_guarded_pin_authorization = 'ussd.reset_guarded_pin_authorization'
    generic_ussd_session['external_session_id'] = os.urandom(20).hex()
    generic_ussd_session['msisdn'] = guardian_account.phone_number
    generic_ussd_session['data'] = {'guarded_account_phone_number': activated_account.phone_number}
    resp = response(activated_account,
                    reset_guarded_pin_authorization,
                    reset_guarded_pin_authorization[5:],
                    init_database,
                    generic_ussd_session)
    assert resp == translation_for(f'{reset_guarded_pin_authorization}.first', preferred_language,
                                   guarded_account_information=activated_account.phone_number)


def test_start(activated_account, cache_balances, cache_preferences, cache_token_data, cache_token_data_list,
               cache_token_symbol_list, celery_session_worker, generic_ussd_session, init_database, load_chain_spec,
               mock_sync_balance_api_query, set_active_token):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    token_symbol = get_active_token_symbol(blockchain_address)
    token_data = get_cached_token_data(blockchain_address, token_symbol)
    decimals = token_data.get("decimals")
    identifier = bytes.fromhex(blockchain_address)
    balances_identifier = [identifier, token_symbol.encode('utf-8')]
    available_balance = get_cached_available_balance(decimals, balances_identifier)
    start = 'ussd.start'
    resp = response(activated_account, start, start[5:], init_database, generic_ussd_session)
    assert resp == translation_for(start,
                                   preferred_language,
                                   account_balance=available_balance,
                                   account_token_name=token_symbol)


def test_token_selection_pin_authorization(activated_account, cache_preferences, cache_token_data, generic_ussd_session,
                                           init_database, set_active_token):
    blockchain_address = activated_account.blockchain_address
    token_symbol = get_active_token_symbol(blockchain_address)
    token_data = get_cached_token_data(blockchain_address, token_symbol)
    preferred_language = get_cached_preferred_language(blockchain_address)
    token_selection_pin_authorization = 'ussd.token_selection_pin_authorization'
    generic_ussd_session['data'] = {'selected_token': token_data}
    resp = response(activated_account,
                    token_selection_pin_authorization,
                    token_selection_pin_authorization[5:],
                    init_database,
                    generic_ussd_session)
    token_name = token_data.get('name')
    token_symbol = token_data.get('symbol')
    token_issuer = token_data.get('issuer')
    token_contact = token_data.get('contact')
    token_location = token_data.get('location')
    data = f'{token_name} ({token_symbol})\n{token_issuer}\n{token_contact}\n{token_location}\n'
    assert resp == translation_for(f'{token_selection_pin_authorization}.first', preferred_language,
                                   token_data=data)


def test_transaction_pin_authorization(activated_account, cache_preferences, cache_token_data, generic_ussd_session,
                                       init_database, set_active_token, valid_recipient):
    blockchain_address = activated_account.blockchain_address
    token_symbol = get_active_token_symbol(blockchain_address)
    token_data = get_cached_token_data(blockchain_address, token_symbol)
    preferred_language = get_cached_preferred_language(blockchain_address)
    decimals = token_data.get("decimals")
    transaction_pin_authorization = 'ussd.transaction_pin_authorization'
    generic_ussd_session['data'] = {
        'recipient_phone_number': valid_recipient.phone_number,
        'transaction_amount': '15'
    }
    resp = response(activated_account, transaction_pin_authorization, transaction_pin_authorization[5:], init_database,
                    generic_ussd_session)
    user_input = generic_ussd_session.get('data').get('transaction_amount')
    transaction_amount = to_wei(decimals, int(user_input))
    tx_recipient_information = valid_recipient.standard_metadata_id()
    tx_sender_information = activated_account.standard_metadata_id()
    assert resp == translation_for(f'{transaction_pin_authorization}.first',
                                   preferred_language,
                                   recipient_information=tx_recipient_information,
                                   transaction_amount=from_wei(decimals, transaction_amount),
                                   token_symbol=token_symbol,
                                   sender_information=tx_sender_information)


def test_guardian_exits(activated_account, cache_preferences, cache_token_data, generic_ussd_session, guardian_account,
                        init_database, set_active_token):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    generic_ussd_session['data'] = {'guardian_phone_number': guardian_account.phone_number}
    # testing exit guardian addition success
    exit_guardian_addition_success = 'ussd.exit_guardian_addition_success'
    resp = response(activated_account, exit_guardian_addition_success, exit_guardian_addition_success[5:],
                    init_database, generic_ussd_session)
    assert resp == translation_for(exit_guardian_addition_success, preferred_language,
                                   guardian_information=guardian_account.standard_metadata_id())

    # testing exit guardian removal success
    exit_guardian_removal_success = 'ussd.exit_guardian_removal_success'
    resp = response(activated_account, exit_guardian_removal_success, exit_guardian_removal_success[5:],
                    init_database, generic_ussd_session)
    assert resp == translation_for(exit_guardian_removal_success, preferred_language,
                                   guardian_information=guardian_account.standard_metadata_id())

    generic_ussd_session['data'] = {'failure_reason': 'foo'}
    # testing exit invalid guardian addition
    exit_invalid_guardian_addition = 'ussd.exit_invalid_guardian_addition'
    resp = response(activated_account, exit_invalid_guardian_addition, exit_invalid_guardian_addition[5:],
                    init_database, generic_ussd_session)
    assert resp == translation_for(exit_invalid_guardian_addition, preferred_language, error_exit='foo')

    # testing exit invalid guardian removal
    exit_invalid_guardian_removal = 'ussd.exit_invalid_guardian_removal'
    resp = response(activated_account, exit_invalid_guardian_removal, exit_invalid_guardian_removal[5:],
                    init_database, generic_ussd_session)
    assert resp == translation_for(exit_invalid_guardian_removal, preferred_language, error_exit='foo')


def test_exit_pin_reset_initiated_success(activated_account, cache_preferences, generic_ussd_session, init_database):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    exit_pin_reset_initiated_success = 'ussd.exit_pin_reset_initiated_success'
    generic_ussd_session['data'] = {'guarded_account_phone_number': activated_account.phone_number}
    resp = response(activated_account, exit_pin_reset_initiated_success, exit_pin_reset_initiated_success[5:],
                    init_database, generic_ussd_session)
    assert resp == translation_for(exit_pin_reset_initiated_success,
                                   preferred_language,
                                   guarded_account_information=activated_account.standard_metadata_id())


def test_exit_insufficient_balance(activated_account, cache_balances, cache_preferences, cache_token_data,
                                   generic_ussd_session, init_database, set_active_token, valid_recipient):
    blockchain_address = activated_account.blockchain_address
    token_symbol = get_active_token_symbol(blockchain_address)
    token_data = get_cached_token_data(blockchain_address, token_symbol)
    preferred_language = get_cached_preferred_language(blockchain_address)
    decimals = token_data.get("decimals")
    identifier = bytes.fromhex(blockchain_address)
    balances_identifier = [identifier, token_symbol.encode('utf-8')]
    available_balance = get_cached_available_balance(decimals, balances_identifier)
    tx_recipient_information = valid_recipient.standard_metadata_id()
    exit_insufficient_balance = 'ussd.exit_insufficient_balance'
    generic_ussd_session['data'] = {
        'recipient_phone_number': valid_recipient.phone_number,
        'transaction_amount': '85'
    }
    transaction_amount = generic_ussd_session.get('data').get('transaction_amount')
    transaction_amount = to_wei(decimals, int(transaction_amount))
    resp = response(activated_account, exit_insufficient_balance, exit_insufficient_balance[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(exit_insufficient_balance,
                                   preferred_language,
                                   amount=from_wei(decimals, transaction_amount),
                                   token_symbol=token_symbol,
                                   recipient_information=tx_recipient_information,
                                   token_balance=available_balance)


def test_exit_invalid_menu_option(activated_account, cache_preferences, generic_ussd_session, init_database,
                                  load_support_phone):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    exit_invalid_menu_option = 'ussd.exit_invalid_menu_option'
    resp = response(activated_account, exit_invalid_menu_option, exit_invalid_menu_option[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(exit_invalid_menu_option, preferred_language, support_phone=Support.phone_number)


def test_exit_pin_blocked(activated_account, cache_preferences, generic_ussd_session, init_database,
                          load_support_phone):
    blockchain_address = activated_account.blockchain_address
    preferred_language = get_cached_preferred_language(blockchain_address)
    exit_pin_blocked = 'ussd.exit_pin_blocked'
    resp = response(activated_account, exit_pin_blocked, exit_pin_blocked[5:], init_database, generic_ussd_session)
    assert resp == translation_for(exit_pin_blocked, preferred_language, support_phone=Support.phone_number)


def test_exit_successful_token_selection(activated_account, cache_preferences, cache_token_data, generic_ussd_session,
                                         init_database, set_active_token):
    blockchain_address = activated_account.blockchain_address
    token_symbol = get_active_token_symbol(blockchain_address)
    token_data = get_cached_token_data(blockchain_address, token_symbol)
    preferred_language = get_cached_preferred_language(blockchain_address)
    exit_successful_token_selection = 'ussd.exit_successful_token_selection'
    generic_ussd_session['data'] = {'selected_token': token_data}
    resp = response(activated_account, exit_successful_token_selection, exit_successful_token_selection[5:],
                    init_database, generic_ussd_session)
    assert resp == translation_for(exit_successful_token_selection, preferred_language, token_symbol=token_symbol)


def test_exit_successful_transaction(activated_account, cache_preferences, cache_token_data, generic_ussd_session,
                                     init_database, set_active_token, valid_recipient):
    blockchain_address = activated_account.blockchain_address
    token_symbol = get_active_token_symbol(blockchain_address)
    token_data = get_cached_token_data(blockchain_address, token_symbol)
    preferred_language = get_cached_preferred_language(blockchain_address)
    decimals = token_data.get("decimals")
    tx_recipient_information = valid_recipient.standard_metadata_id()
    tx_sender_information = activated_account.standard_metadata_id()
    exit_successful_transaction = 'ussd.exit_successful_transaction'
    generic_ussd_session['data'] = {
        'recipient_phone_number': valid_recipient.phone_number,
        'transaction_amount': '15'
    }
    transaction_amount = generic_ussd_session.get('data').get('transaction_amount')
    transaction_amount = to_wei(decimals, int(transaction_amount))
    resp = response(activated_account, exit_successful_transaction, exit_successful_transaction[5:], init_database,
                    generic_ussd_session)
    assert resp == translation_for(exit_successful_transaction,
                                   preferred_language,
                                   transaction_amount=from_wei(decimals, transaction_amount),
                                   token_symbol=token_symbol,
                                   recipient_information=tx_recipient_information,
                                   sender_information=tx_sender_information)
