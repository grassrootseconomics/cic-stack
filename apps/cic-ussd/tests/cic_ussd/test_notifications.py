# standard imports

# external imports
import pytest

# local imports
from cic_ussd.notifications import Notifier


@pytest.mark.parametrize("key, preferred_language, recipient, expected_message", [
    ("ussd.exit", "en", "+254712345678", "END Thank you for using the service."),
    ("ussd.exit", "sw", "+254712345678", "END Asante kwa kutumia huduma")
])
def test_send_sms_notification(celery_session_worker,
                               expected_message,
                               key,
                               mock_notifier_api,
                               preferred_language,
                               recipient,
                               set_locale_files):
    notifier = Notifier()
    notifier.queue = None
    notifier.send_sms_notification(key=key, phone_number=recipient, preferred_language=preferred_language)
    assert mock_notifier_api.get('message') == expected_message
    assert mock_notifier_api.get('recipient') == recipient







