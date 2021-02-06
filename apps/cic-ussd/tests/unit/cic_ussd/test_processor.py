# local imports
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.processor import (custom_display_text,
                                next_state,
                                process_request,
                                process_pin_authorization,
                                process_transaction_pin_authorization,
                                process_exit_insufficient_balance,
                                process_exit_successful_transaction)


def test_process_pin_authorization(create_activated_user,
                                   load_ussd_menu,
                                   set_locale_files):
    ussd_menu = UssdMenu.find_by_name(name='name_management_pin_authorization')
    response = process_pin_authorization(
        display_key=ussd_menu.get('display_key'),
        user=create_activated_user
    )
    assert response == 'CON Please enter your PIN.\n0. Back'

    user_with_one_failed_pin_attempt = create_activated_user
    user_with_one_failed_pin_attempt.failed_pin_attempts = 1
    alt_response = process_pin_authorization(
        display_key=ussd_menu.get('display_key'),
        user=user_with_one_failed_pin_attempt,
    )
    assert alt_response == 'CON Please enter your PIN. You have 2 attempts remaining.\n0. Back'


def test_process_transaction_pin_authorization(create_activated_user,
                                               create_in_db_ussd_session,
                                               load_ussd_menu,
                                               set_locale_files):
    session_data = {
        'recipient_phone_number': '+254700000000',
    }
    ussd_session = create_in_db_ussd_session.to_json()
    ussd_session['session_data'] = session_data
    ussd_session['user_input'] = '1*0700000000*120'
    ussd_menu = UssdMenu.find_by_name(name='transaction_pin_authorization')
    response = process_transaction_pin_authorization(
        display_key=ussd_menu.get('display_key'),
        user=create_activated_user,
        ussd_session=ussd_session
    )
    assert response == 'CON +254700000000 will receive 120.00 SRF from +25498765432.\nPlease enter your PIN to confirm.\n0. Back'


def test_process_request_for_pending_user(load_ussd_menu, create_pending_user):
    expected_menu = process_request(user_input="", user=create_pending_user)
    assert expected_menu == UssdMenu.find_by_name(name='initial_language_selection')


def test_processor_request_for_activated_user(load_ussd_menu, create_activated_user):
    expected_menu = process_request(user_input="", user=create_activated_user)
    assert expected_menu == UssdMenu.find_by_name(name="start")


def test_next_state(load_data_into_state_machine, load_ussd_menu, create_in_db_ussd_session, create_pending_user):
    assert create_in_db_ussd_session.state == "initial_language_selection"
    successive_state = next_state(
        ussd_session=create_in_db_ussd_session.to_json(),
        user=create_pending_user,
        user_input="1"
    )
    assert successive_state == "initial_pin_entry"


def test_custom_display_text(create_activated_user,
                             get_in_redis_ussd_session,
                             load_ussd_menu,
                             set_locale_files):
    ussd_session = get_in_redis_ussd_session
    user = create_activated_user
    ussd_menu = UssdMenu.find_by_name(name='exit_invalid_request')
    english_translation = custom_display_text(
        display_key=ussd_menu.get('display_key'),
        menu_name=ussd_menu.get('name'),
        user=user,
        ussd_session=ussd_session
    )
    user.preferred_language = 'sw'
    swahili_translation = custom_display_text(
        display_key=ussd_menu.get('display_key'),
        menu_name=ussd_menu.get('name'),
        user=user,
        ussd_session=ussd_session
    )
    assert swahili_translation == 'END Chaguo si sahihi.'
    assert english_translation == 'END Invalid request.'


def test_process_exit_insufficient_balance(
        create_valid_tx_recipient,
        load_ussd_menu,
        mock_balance,
        set_locale_files,
        ussd_session_data):
    mock_balance(50)
    ussd_session_data['user_input'] = f'1*{create_valid_tx_recipient.phone_number}*75'
    ussd_session_data['session_data'] = {'recipient_phone_number': create_valid_tx_recipient.phone_number}
    ussd_session_data['display_key'] = 'exit_insufficient_balance'
    ussd_menu = UssdMenu.find_by_name(name='exit_insufficient_balance')
    response = process_exit_insufficient_balance(
        display_key=ussd_menu.get('display_key'),
        user=create_valid_tx_recipient,
        ussd_session=ussd_session_data
    )
    assert response == 'CON Payment of 75.00 SRF to +25498765432 has failed due to insufficent balance.\nYour Sarafu-Network balances is: 50.00\n00. Back\n99. Exit'


def test_process_exit_successful_transaction(
        create_valid_tx_recipient,
        create_valid_tx_sender,
        load_ussd_menu,
        set_locale_files,
        ussd_session_data):
    ussd_session_data['session_data'] = {
        'recipient_phone_number': create_valid_tx_recipient.phone_number,
        'transaction_amount': 75
    }
    ussd_session_data['display_key'] = 'exit_successful_transaction'
    ussd_menu = UssdMenu.find_by_name(name='exit_successful_transaction')
    response = process_exit_successful_transaction(
        display_key=ussd_menu.get('display_key'),
        user=create_valid_tx_sender,
        ussd_session=ussd_session_data
    )
    assert response == 'CON Your request has been sent. +25498765432 will receive 75.00 SRF from +25498765433.\n00. Back\n99. Exit'
