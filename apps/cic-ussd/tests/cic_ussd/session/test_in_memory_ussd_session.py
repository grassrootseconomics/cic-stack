# standard imports
import json

# local imports
from cic_ussd.menu.ussd_menu import UssdMenu
from cic_ussd.session.ussd_session import UssdSession


def test_ussd_session(load_ussd_menu, get_in_redis_ussd_session):
    ussd_session = get_in_redis_ussd_session
    assert UssdMenu.find_by_name(name='initial_language_selection').get('name') == ussd_session.state
