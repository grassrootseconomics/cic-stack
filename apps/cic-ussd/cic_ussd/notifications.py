# standard imports
from typing import Union

# third-party imports
from cic_notify.api import Api

# local imports
from cic_ussd.translation import translation_for


class Notifier:

    queue: Union[str, bool, None] = False

    def send_sms_notification(self, key: str, phone_number: str, preferred_language: str, **kwargs):
        """This function creates a task to send a message to a user.
        :param key: The key mapping to a specific message entry in translation files.
        :type key: str
        :param phone_number: The recipient's phone number.
        :type phone_number: str
        :param preferred_language: A notification recipient's preferred language.
        :type preferred_language: str
        """
        notify_api = Api() if self.queue is False else Api(queue=self.queue)
        message = translation_for(key=key, preferred_language=preferred_language, **kwargs)
        notify_api.sms(recipient=phone_number, message=message)
