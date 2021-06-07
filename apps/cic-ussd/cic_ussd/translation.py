"""
This module is responsible for translation of ussd menu text based on a user's set preferred language.
"""
import i18n
from typing import Optional


def translation_for(key: str, preferred_language: Optional[str] = None, **kwargs) -> str:
    """
    Translates text mapped to a specific YAML key into the user's set preferred language.
    :param preferred_language: Account's preferred language in which to view the ussd menu.
    :type preferred_language str
    :param key: Key to a specific YAML test entry
    :type key: str
    :param kwargs: Dynamic values to be interpolated into the YAML texts for specific keys
    :type kwargs: any
    :return: Appropriately translated text for corresponding provided key
    :rtype: str
    """
    if preferred_language:
        i18n.set('locale', preferred_language)
    else:
        i18n.set('locale', i18n.config.get('fallback'))
    return i18n.t(key, **kwargs)
