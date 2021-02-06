# local imports
from cic_ussd.state_machine.logic.menu import (menu_one_selected,
                                               menu_two_selected,
                                               menu_three_selected,
                                               menu_four_selected)


def test_menu_selection(create_pending_user, create_in_db_ussd_session):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    assert menu_one_selected(('1', serialized_in_db_ussd_session, create_pending_user)) is True
    assert menu_one_selected(('x', serialized_in_db_ussd_session, create_pending_user)) is False

    assert menu_two_selected(('2', serialized_in_db_ussd_session, create_pending_user)) is True
    assert menu_two_selected(('1', serialized_in_db_ussd_session, create_pending_user)) is False

    assert menu_three_selected(('3', serialized_in_db_ussd_session, create_pending_user)) is True
    assert menu_three_selected(('4', serialized_in_db_ussd_session, create_pending_user)) is False

    assert menu_four_selected(('4', serialized_in_db_ussd_session, create_pending_user)) is True
    assert menu_four_selected(('d', serialized_in_db_ussd_session, create_pending_user)) is False

