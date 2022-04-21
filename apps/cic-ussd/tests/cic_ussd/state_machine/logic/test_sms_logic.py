# standard imports
import json

# external imports

# local imports
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.account.tokens import get_default_token_symbol
from cic_ussd.cache import get_cached_data
from cic_ussd.phone_number import Support
from cic_ussd.state_machine.logic.sms import upsell_unregistered_recipient
from cic_ussd.translation import translation_for


# tests imports


def test_upsell_unregistered_recipient(activated_account,
                                       cache_default_token_data,
                                       cache_preferences,
                                       cached_ussd_session,
                                       init_database,
                                       load_support_phone,
                                       mock_notifier_api,
                                       set_locale_files,
                                       set_active_token,
                                       valid_recipient):
    state_machine_data = (valid_recipient.phone_number, cached_ussd_session.to_json(), activated_account, init_database)
    upsell_unregistered_recipient(state_machine_data)
    preferred_language = get_cached_preferred_language(activated_account.blockchain_address)
    token_symbol = get_default_token_symbol()
    tx_sender_information = activated_account.standard_metadata_id()
    message = translation_for('sms.upsell_unregistered_recipient',
                              preferred_language,
                              tx_sender_information=tx_sender_information,
                              token_symbol=token_symbol,
                              support_phone=Support.phone_number)
    assert mock_notifier_api.get('message') == message
    assert mock_notifier_api.get('recipient') == valid_recipient.phone_number
