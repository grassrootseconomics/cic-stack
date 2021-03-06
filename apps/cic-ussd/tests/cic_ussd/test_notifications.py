# standard imports

# third-party imports
import pytest

# local imports
from cic_ussd.notifications import Notifier


@pytest.mark.parametrize("key, preferred_language, recipient, expected_message", [
    ("ussd.kenya.exit", "en", "+254712345678", "END Thank you for using the service."),
    ("ussd.kenya.exit", "sw", "+254712345678", "END Asante kwa kutumia huduma.")
])
def test_send_sms_notification(celery_session_worker,
                               expected_message,
                               key,
                               preferred_language,
                               recipient,
                               set_locale_files,
                               mock_notifier_api):

    notifier = Notifier()
    notifier.queue = None

    notifier.send_sms_notification(key=key, phone_number=recipient, preferred_language=preferred_language)
    messages = mock_notifier_api

    assert messages[0].get('message') == expected_message
    assert messages[0].get('recipient') == recipient







