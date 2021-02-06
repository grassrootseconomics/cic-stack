# standard imports

# third-party imports
import pytest

# local imports
from cic_ussd.state_machine.logic.sms import (send_terms_to_user_if_required,
                                              process_mini_statement_request,
                                              upsell_unregistered_recipient)


def test_send_terms_to_user_if_required(caplog,
                                        create_in_db_ussd_session,
                                        create_activated_user):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('', serialized_in_db_ussd_session, create_activated_user)
    send_terms_to_user_if_required(state_machine_data=state_machine_data)
    assert 'Requires integration to cic-notify.' in caplog.text


def test_process_mini_statement_request(caplog,
                                        create_in_db_ussd_session,
                                        create_activated_user):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('', serialized_in_db_ussd_session, create_activated_user)
    process_mini_statement_request(state_machine_data=state_machine_data)
    assert 'Requires integration to cic-notify.' in caplog.text


def test_upsell_unregistered_recipient(caplog,
                                       create_in_db_ussd_session,
                                       create_activated_user):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine_data = ('', serialized_in_db_ussd_session, create_activated_user)
    upsell_unregistered_recipient(state_machine_data=state_machine_data)
    assert 'Requires integration to cic-notify.' in caplog.text
