# standard imports
import json
from typing import Tuple

# external imports
import celery
import i18n
from cic_types.condiments import MetadataPointer
from sqlalchemy.orm.session import Session

# local imports
from cic_ussd.cache import cache_data_key, get_cached_data
from cic_ussd.db.models.account import Account
from cic_ussd.processor.poller import wait_for_cache, wait_for_session_data
from cic_ussd.session.ussd_session import save_session_data
from cic_ussd.translation import Languages


def is_valid_language_selection(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data

    key = cache_data_key('system:languages'.encode('utf-8'), MetadataPointer.NONE)
    cached_system_languages = get_cached_data(key)
    language_list = json.loads(cached_system_languages)

    if not language_list:
        wait_for_cache(identifier='system:languages'.encode('utf-8'), resource_name='Languages list', salt=MetadataPointer.NONE)

    if user_input in ['00', '11', '22']:
        return False
    user_input = int(user_input)
    return user_input <= len(language_list)


def change_preferred_language(state_machine_data: Tuple[str, dict, Account, Session]):
    """
    :param state_machine_data:
    :type state_machine_data:
    :return:
    :rtype:
    """
    user_input, ussd_session, account, session = state_machine_data
    preferred_language = preferred_langauge_from_selection(user_input=user_input)
    preferences_data = {
        'preferred_language': preferred_language
    }

    s = celery.signature(
        'cic_ussd.tasks.metadata.add_preferences_metadata',
        [account.blockchain_address, preferences_data],
        queue='cic-ussd'
    )
    return s.apply_async()


def preferred_langauge_from_selection(user_input: str):
    """
    :param user_input:
    :type user_input:
    :return:
    :rtype:
    """
    key = cache_data_key('system:languages'.encode('utf-8'), MetadataPointer.NONE)
    cached_system_languages = get_cached_data(key)
    language_list = json.loads(cached_system_languages)
    user_input = int(user_input)
    selected_language = language_list[user_input - 1]
    preferred_language = i18n.config.get('fallback')
    for key, value in Languages.languages_dict.items():
        if selected_language[3:] == value:
            preferred_language = key
    return preferred_language
