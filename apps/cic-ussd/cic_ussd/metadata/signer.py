# standard imports
import json
import logging
from typing import Optional
from urllib.request import Request, urlopen

# third-party imports
import gnupg

# local imports

logg = logging.getLogger()


class Signer:
    """
    :cvar gpg_path:
    :type gpg_path:
    :cvar gpg_passphrase:
    :type gpg_passphrase:
    :cvar key_file_path:
    :type key_file_path:

    """
    gpg_path: str = None
    gpg_passphrase: str = None
    key_file_path: str = None

    def __init__(self):
        self.gpg = gnupg.GPG(gnupghome=self.gpg_path)

        with open(self.key_file_path, 'r') as key_file:
            self.key_data = key_file.read()

    def get_operational_key(self):
        """
        :return:
        :rtype:
        """
        # import key data into keyring
        self.gpg.import_keys(key_data=self.key_data)
        gpg_keys = self.gpg.list_keys()
        key_algorithm = gpg_keys[0].get('algo')
        key_id = gpg_keys[0].get("keyid")
        logg.debug(f'using signing key: {key_id}, algorithm: {key_algorithm}')
        return gpg_keys[0]

    def sign_digest(self, data: dict):
        """
        :param data:
        :type data:
        :return:
        :rtype:
        """
        digest = data['digest']
        key_id = self.get_operational_key().get('keyid')
        signature = self.gpg.sign(digest, passphrase=self.gpg_passphrase, keyid=key_id)
        return str(signature)


