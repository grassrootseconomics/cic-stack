# standard imports

# external imports

# local imports
from cic_ussd.state_machine.logic.menu import (menu_one_selected,
                                               menu_two_selected,
                                               menu_three_selected,
                                               menu_four_selected,
                                               menu_five_selected,
                                               menu_six_selected,
                                               menu_nine_selected,
                                               menu_zero_zero_selected,
                                               menu_eleven_selected,
                                               menu_twenty_two_selected,
                                               menu_ninety_nine_selected)

# test imports


def test_menu_selection(init_database, pending_account, persisted_ussd_session):
    ussd_session = persisted_ussd_session.to_json()
    assert menu_one_selected(('1', ussd_session, pending_account, init_database)) is True
    assert menu_one_selected(('x', ussd_session, pending_account, init_database)) is False
    assert menu_two_selected(('2', ussd_session, pending_account, init_database)) is True
    assert menu_two_selected(('1', ussd_session, pending_account, init_database)) is False
    assert menu_three_selected(('3', ussd_session, pending_account, init_database)) is True
    assert menu_three_selected(('4', ussd_session, pending_account, init_database)) is False
    assert menu_four_selected(('4', ussd_session, pending_account, init_database)) is True
    assert menu_four_selected(('d', ussd_session, pending_account, init_database)) is False
    assert menu_five_selected(('5', ussd_session, pending_account, init_database)) is True
    assert menu_five_selected(('e', ussd_session, pending_account, init_database)) is False
    assert menu_six_selected(('6', ussd_session, pending_account, init_database)) is True
    assert menu_six_selected(('8', ussd_session, pending_account, init_database)) is False
    assert menu_nine_selected(('9', ussd_session, pending_account, init_database)) is True
    assert menu_nine_selected(('-', ussd_session, pending_account, init_database)) is False
    assert menu_zero_zero_selected(('00', ussd_session, pending_account, init_database)) is True
    assert menu_zero_zero_selected(('/', ussd_session, pending_account, init_database)) is False
    assert menu_eleven_selected(('11', ussd_session, pending_account, init_database)) is True
    assert menu_eleven_selected(('*', ussd_session, pending_account, init_database)) is False
    assert menu_twenty_two_selected(('22', ussd_session, pending_account, init_database)) is True
    assert menu_twenty_two_selected(('5', ussd_session, pending_account, init_database)) is False
    assert menu_ninety_nine_selected(('99', ussd_session, pending_account, init_database)) is True
    assert menu_ninety_nine_selected(('d', ussd_session, pending_account, init_database)) is False


