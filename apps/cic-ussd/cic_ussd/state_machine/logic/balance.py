# standard imports
import logging
from typing import Tuple

# third-party imports

# local imports
from cic_ussd.db.models.user import User

logg = logging.getLogger(__file__)


def process_mini_statement_request(state_machine_data: Tuple[str, dict, User]):
    """This function compiles a brief statement of a user's last three inbound and outbound transactions and send the
    same as a message on their selected avenue for notification.
    :param state_machine_data: A tuple containing user input, a ussd session and user object.
    :type state_machine_data: str
    """
    user_input, ussd_session, user = state_machine_data
    logg.debug('This section requires integration with cic-eth. (The last 6 transactions would be sent as an sms.)')
