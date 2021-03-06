# local imports
from cic_ussd.state_machine import UssdStateMachine


def test_state_machine(create_in_db_ussd_session,
                       get_in_redis_ussd_session,
                       load_data_into_state_machine,
                       create_pending_user):
    serialized_in_db_ussd_session = create_in_db_ussd_session.to_json()
    state_machine = UssdStateMachine(ussd_session=get_in_redis_ussd_session.to_json())
    state_machine.scan_data(('1', serialized_in_db_ussd_session, create_pending_user))
    assert state_machine.state == 'initial_pin_entry'
