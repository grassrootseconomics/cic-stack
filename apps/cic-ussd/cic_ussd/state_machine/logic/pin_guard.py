# standard imports
import logging
from typing import Tuple

# external imports
import celery
import i18n
from phonenumbers.phonenumberutil import NumberParseException
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.account.guardianship import Guardianship
from cic_ussd.account.metadata import get_cached_preferred_language
from cic_ussd.db.models.account import Account
from cic_ussd.db.models.base import SessionBase
from cic_ussd.notifications import Notifier
from cic_ussd.phone_number import process_phone_number, E164Format
from cic_ussd.session.ussd_session import save_session_data
from cic_ussd.translation import translation_for


logg = logging.getLogger(__file__)


def save_guardian_to_session_data(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    session_data = ussd_session.get('data') or {}
    session_data['guardian_phone_number'] = user_input.replace(" ", "")
    save_session_data('cic-ussd', session, session_data, ussd_session)


def save_guarded_account_session_data(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    session_data = ussd_session.get('data') or {}
    session_data['guarded_account_phone_number'] = user_input.replace(" ", "")
    save_session_data('cic-ussd', session, session_data, ussd_session)


def retrieve_person_metadata(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    guardian = Account.get_by_phone_number(user_input, session)
    blockchain_address = guardian.blockchain_address
    s_query_person_metadata = celery.signature(
        'cic_ussd.tasks.metadata.query_person_metadata', [blockchain_address], queue='cic-ussd')
    s_query_person_metadata.apply_async()


def is_valid_guardian_addition(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    user_input = user_input.replace(" ", "")
    preferred_language = get_cached_preferred_language(account.blockchain_address)
    if not preferred_language:
        preferred_language = i18n.config.get('fallback')

    is_valid_account = Account.get_by_phone_number(user_input, session) is not None
    guardianship = Guardianship()
    is_system_guardian = guardianship.is_system_guardian(user_input)
    is_initiator = user_input == account.phone_number
    is_existent_guardian = user_input in account.get_guardians() or is_system_guardian

    failure_reason = ''
    if not is_valid_account:
        failure_reason = translation_for('helpers.error.no_matching_account', preferred_language)

    if is_initiator:
        failure_reason = translation_for('helpers.error.is_initiator', preferred_language)

    if is_existent_guardian:
        failure_reason = translation_for('helpers.error.is_existent_guardian', preferred_language)

    if failure_reason:
        session_data = ussd_session.get('data') or {}
        session_data['failure_reason'] = failure_reason
        save_session_data('cic-ussd', session, session_data, ussd_session)

    return user_input is not None and is_valid_account and not is_existent_guardian and not is_initiator and not is_system_guardian


def add_pin_guardian(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    guardian_phone_number = ussd_session.get('data').get('guardian_phone_number')
    account.add_guardian(guardian_phone_number)
    session.add(account)
    session.flush()
    SessionBase.release_session(session=session)


def is_set_pin_guardian(account: Account, checked_number: str, preferred_language: str, session: Session, ussd_session: dict):
    """"""
    failure_reason = ''
    set_guardians = []
    if account:
        set_guardians = account.get_guardians()
    else:
        failure_reason = translation_for('helpers.error.no_matching_account', preferred_language)

    # e164 is not enforced on phone numbers within the ussd setup as such all checked guardians should be checked in
    # both e164 or entered format.
    processed_guardian = None
    for guardian in set_guardians:
        processed_guardian = process_phone_number(phone_number=guardian, region=E164Format.region)

    set_guardians.append(processed_guardian)

    is_set_guardian = checked_number in set_guardians or process_phone_number(phone_number=checked_number, region=E164Format.region) in set_guardians
    is_initiator = checked_number == account.phone_number

    guardianship = Guardianship()
    is_system_guardian = guardianship.is_system_guardian(checked_number)

    if not is_set_guardian:
        failure_reason = translation_for('helpers.error.is_not_existent_guardian', preferred_language)

    if is_initiator:
        failure_reason = translation_for('helpers.error.is_initiator', preferred_language)

    if failure_reason:
        session_data = ussd_session.get('data') or {}
        session_data['failure_reason'] = failure_reason
        save_session_data('cic-ussd', session, session_data, ussd_session)

    return (is_set_guardian or is_system_guardian) and not is_initiator


def is_dialers_pin_guardian(state_machine_data: Tuple[str, dict, Account, Session]):
    user_input, ussd_session, account, session = state_machine_data
    preferred_language = get_cached_preferred_language(account.blockchain_address)
    if not preferred_language:
        preferred_language = i18n.config.get('fallback')
    return is_set_pin_guardian(account, user_input, preferred_language, session, ussd_session)


def is_others_pin_guardian(state_machine_data: Tuple[str, dict, Account, Session]):
    user_input, ussd_session, account, session = state_machine_data
    preferred_language = get_cached_preferred_language(account.blockchain_address)
    guarded_account = Account.get_by_phone_number(user_input, session)
    if not preferred_language:
        preferred_language = i18n.config.get('fallback')
    return is_set_pin_guardian(guarded_account, account.phone_number, preferred_language, session, ussd_session)


def remove_pin_guardian(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    guardian_phone_number = ussd_session.get('data').get('guardian_phone_number')
    account.remove_guardian(guardian_phone_number)
    session.add(account)
    session.flush()
    SessionBase.release_session(session=session)


def initiate_pin_reset(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    session_data = ussd_session.get('data')
    quorum_count = session_data['quorum_count'] if session_data.get('quorum_count') else 0
    quorum_count += 1
    session_data['quorum_count'] = quorum_count
    save_session_data('cic-ussd', session, session_data, ussd_session)
    guarded_account_phone_number = session_data.get('guarded_account_phone_number')
    guarded_account = Account.get_by_phone_number(guarded_account_phone_number, session)

    if quorum_count >= guarded_account.guardian_quora:
        guarded_account.reset_pin(session)
        logg.debug(f'Reset initiated for: {guarded_account.phone_number}')
        session_data['quorum_count'] = 0
        save_session_data('cic-ussd', session, session_data, ussd_session)

        preferred_language = get_cached_preferred_language(guarded_account.blockchain_address)
        if not preferred_language:
            preferred_language = i18n.config.get('fallback')

        notifier = Notifier()
        notifier.send_sms_notification(
            key='sms.pin_reset_initiated',
            phone_number=guarded_account.phone_number,
            preferred_language=preferred_language,
            pin_initiator=account.standard_metadata_id())
