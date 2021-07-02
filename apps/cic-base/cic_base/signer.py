# standard imports
import logging
import os

# external imports 
from crypto_dev_signer.eth.signer import ReferenceSigner as EIP155Signer
from crypto_dev_signer.keystore.dict import DictKeystore

logg = logging.getLogger(__name__)

keystore = DictKeystore()

default_passphrase = os.environ.get('ETH_PASSPHRASE', '')


def from_keystore(keyfile, passphrase=default_passphrase):
    global keystore

    # signer
    if keyfile == None:
        raise ValueError('please specify signer keystore file')

    logg.debug('loading keystore file {}'.format(keyfile))
    address = keystore.import_keystore_file(keyfile, password=passphrase)

    signer = EIP155Signer(keystore)
    return (address, signer,)
