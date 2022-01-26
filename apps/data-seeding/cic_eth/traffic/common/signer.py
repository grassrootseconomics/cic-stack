# standard imports
import logging

# external imports 
from funga.eth.signer import EIP155Signer
from funga.eth.keystore.dict import DictKeystore

logg = logging.getLogger(__name__)

keystore = DictKeystore()

def from_keystore(keyfile):
    global keystore

    # signer
    if keyfile == None:
        raise ValueError('please specify signer keystore file')

    logg.debug('loading keystore file {}'.format(keyfile))
    address = keystore.import_keystore_file(keyfile)

    signer = EIP155Signer(keystore)
    return (address, signer,)
