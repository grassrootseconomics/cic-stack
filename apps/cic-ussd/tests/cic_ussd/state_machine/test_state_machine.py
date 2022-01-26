# local imports
from cic_ussd.state_machine import UssdStateMachine


def test_state_machine(activated_account_ussd_session,
                       celery_session_worker,
                       init_database,
                       init_state_machine,
                       load_languages,
                       pending_account,
                       set_locale_files):
    state_machine = UssdStateMachine(activated_account_ussd_session)
    state_machine.scan_data(('1', activated_account_ussd_session, pending_account, init_database))
    assert state_machine.__repr__() == f'<KenyaUssdStateMachine: {state_machine.state}>'
    assert state_machine.state == 'account_creation_prompt'
