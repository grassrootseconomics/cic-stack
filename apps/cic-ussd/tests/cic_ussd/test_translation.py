# standard imports

# external imports

# local imports
from cic_ussd.translation import translation_for

# tests imports


def test_translation_for(set_locale_files):
    english_translation = translation_for(
        key='ussd.exit_invalid_request',
        preferred_language='en'
    )
    swahili_translation = translation_for(
        key='ussd.exit_invalid_request',
        preferred_language='sw'
    )
    assert swahili_translation == 'END Chaguo si sahihi'
    assert english_translation == 'END Invalid request.'
