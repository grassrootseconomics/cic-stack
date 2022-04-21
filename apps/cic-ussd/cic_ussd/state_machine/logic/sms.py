# standard imports
from typing import Tuple

# external imports
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.account.tokens import get_active_token_symbol
from cic_ussd.db.models.account import Account
from cic_ussd.notifications import Notifier
from cic_ussd.phone_number import E164Format, Support, process_phone_number


def upsell_unregistered_recipient(state_machine_data: Tuple[str, dict, Account, Session]):
    """"""
    user_input, ussd_session, account, session = state_machine_data
    notifier = Notifier()
    phone_number = process_phone_number(user_input, E164Format.region)
    preferred_language = get_cached_preferred_language(account.blockchain_address)
    token_symbol = get_active_token_symbol(account.blockchain_address)
    tx_sender_information = account.standard_metadata_id()
    notifier.send_sms_notification('sms.upsell_unregistered_recipient',
                                   phone_number,
                                   preferred_language,
                                   tx_sender_information=tx_sender_information,
                                   token_symbol=token_symbol,
                                   support_phone=Support.phone_number)
