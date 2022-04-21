"""
This module is responsible for translation of ussd menu text based on a user's set preferred language.
"""
# standard imports
import json

import i18n
import os
from pathlib import Path
from typing import Optional

# external imports
from cic_translations.processor import generate_translation_files, parse_csv
from cic_types.condiments import MetadataPointer

# local imports
from cic_ussd.cache import cache_data, cache_data_key
from cic_ussd.validator import validate_presence


def generate_locale_files(locale_dir: str, schema_file_path: str, translation_builder_path: str):
    """"""
    translation_builder_files = os.listdir(translation_builder_path)
    for file in translation_builder_files:
        props = Path(file)
        if props.suffix == '.csv':
            parsed_csv = parse_csv(os.path.join(translation_builder_path, file))
            generate_translation_files(
                parsed_csv=parsed_csv,
                schema_file_path=schema_file_path,
                translation_file_type=props.stem,
                translation_file_path=locale_dir
            )


class Languages:
    languages_dict: dict = None

    @classmethod
    def load_languages_dict(cls, languages_file: str):
        with open(languages_file, "r") as languages_file:
            cls.languages_dict = json.load(languages_file)

    def cache_system_languages(self):
        system_languages: list = list(self.languages_dict.values())
        languages_list = []
        for i in range(len(system_languages)):
            language = f'{i + 1}. {system_languages[i]}'
            languages_list.append(language)

        key = cache_data_key('system:languages'.encode('utf-8'), MetadataPointer.NONE)
        cache_data(key, json.dumps(languages_list))


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
