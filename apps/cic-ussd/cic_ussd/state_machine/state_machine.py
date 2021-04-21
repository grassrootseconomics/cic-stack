# standard imports
import logging

# third party imports
from transitions import Machine

# local imports

logg = logging.getLogger(__name__)


class UssdStateMachine(Machine):
    """This class describes a finite state machine responsible for maintaining all the states that describe the ussd
    menu  as well as providing a means for navigating through these states based on different user inputs.
    It defines different helper functions that co-ordinate with the stakeholder components of the ussd menu: i.e  the
    Account, UssdSession, UssdMenu to facilitate user interaction with ussd menu.
    :cvar states: A list of pre-defined states.
    :type states: list
    :cvar transitions: A list of pre-defined transitions.
    :type transitions: list
    """
    states = []
    transitions = []

    def __repr__(self):
        return f'<KenyaUssdStateMachine: {self.state}>'

    def __init__(self, ussd_session: dict):
        """
        :param ussd_session: A Ussd session object that contains contextual data that informs the state machine's state
        changes.
        :type ussd_session: dict
        """
        self.ussd_session = ussd_session
        super(UssdStateMachine, self).__init__(initial=ussd_session.get('state'),
                                               model=self,
                                               states=self.states,
                                               transitions=self.transitions)
