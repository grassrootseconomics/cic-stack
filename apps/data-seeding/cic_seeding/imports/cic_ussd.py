# standard imports
import logging
import urllib.request
import urllib.parse
import uuid
import os
import json
import threading
import time

# external imports
from urlybird.host import url_apply_port_string
import phonenumbers
from cic_types.processor import (
        generate_metadata_pointer,
        phone_number_to_e164,
        )
from cic_types.condiments import MetadataPointer

# local imports
from cic_seeding.imports import (
        Importer,
        ImportUser,
        )
from cic_seeding.index import (
        AddressQueue,
        SeedQueue,
        )
from cic_seeding.chain import (
        TamperedBlock,
        )

logg = logging.getLogger()


# Assemble the USSD provider url from the given configuration.
def _ussd_url(config):
    url_parts = urllib.parse.urlsplit(config.get('USSD_PROVIDER'))
    qs = urllib.parse.urlencode([
                ('username', config.get('USSD_USER')),
                ('password', config.get('USSD_PASS')),
            ]
            )
    url = urllib.parse.urlunsplit((url_parts[0], url_parts[1], url_parts[2], qs, '',))
    return str(url)


# Return True if config defines an SSL connection to the USSD provider.
def _ussd_ssl(config):
    url_parts = urllib.parse.urlsplit(config.get('USSD_PROVIDER'))
    if url_parts[0] == 'https':
        return True
    return False


# A simple urllib request factory
# Should be enough unless fancy stuff is needed for authentication etc.
def default_req_factory(meta_url, ptr):
        url = urllib.parse.urljoin(meta_url, ptr)
        return urllib.request.Request(url=url)



# Worker thread that receives user objects for import.
# It polls for the associated blockchain address (the "phone pointer").
# Once retrieved it adds the identity entry to the user object, and adds it to the data folder for new user processing.
class CicUssdConnectWorker(threading.Thread):

    req_factory = default_req_factory
    delay = 1
    max_tries = 0

    # The side of the job_queue will throttle the resource usage
    def __init__(self, idx, importer, meta_url, job_queue):
        super(CicUssdConnectWorker, self).__init__()
        self.meta_url = meta_url
        self.imp = importer
        self.q = job_queue
        self.idx = idx
   

    def run(self):
        i = 0
        while True:
            u = self.q.get()
            if u == None:
                return
            self.process(i, u)
            i += 1


    def process(self, i, u):
        ph = phone_number_to_e164(u.phone, None)
        ph_bytes = ph.encode('utf-8')
        self.ptr = generate_metadata_pointer(ph_bytes, MetadataPointer.PHONE)
        self.req = CicUssdConnectWorker.req_factory(self.meta_url, self.ptr)

        tries = 0

        address = None
        while True:
            r = None
            tries += 1
            try:
                r = urllib.request.urlopen(self.req)
                address = json.load(r)
                break 
            except urllib.error.HTTPError:
                if self.max_tries > 0 and self.max_tries == tries:
                    raise RuntimeError('cannot find metadata resource {} -> {}'.format(ph, self.ptr))
                time.sleep(self.delay)
            
            if r == None:
                continue
    
        logg.debug('have address {} for phone {}'.format(address, ph))

        idx = float('{}.{}'.format(self.idx, i))
        self.imp.process_address(idx, u, address)


def apply_default_stores(stores={}):
    store_path = os.path.join(config.get('_USERDIR'), 'ussd_tx_src')
    blocktx_store = SeedQueue(store_path, key_normalizer=normalize_key)

    store_path = os.path.join(config.get('_USERDIR'), 'ussd_phone')
    unconnected_phone_store = AddressQueue(store_path)

    stores['ussd_tx_src'] = blocktx_store
    stores['ussd_phone'] =unconnected_phone_store

    return stores


# Links the user data in a separate directory for separate processing. (e.g. by CicUssdConnectWorker).
# Also provides the sync filter that stores block transactions for deferred processing.
class CicUssdImporter(Importer):

    def __init__(self, config, rpc, signer, signer_address, stores={}, default_tag=[]):
        super(CicUssdImporter, self).__init__(config, rpc, signer, signer_address, stores=stores, default_tag=default_tag)

        self.ussd_provider = config.get('USSD_PROVIDER')
        self.ussd_valid_service_codes = config.get('USSD_SERVICE_CODE').split(',')
        self.ussd_service_code = self.ussd_valid_service_codes[0]
        self.ussd_url = _ussd_url(config) 
        self.ussd_provider_ssl = _ussd_ssl(config)


    def _build_ussd_request(self, phone_number, service_code, txt=None):
        session = uuid.uuid4().hex
        if txt == None:
            txt = service_code
        data = {
            'sessionId': session,
            'serviceCode': service_code,
            'phoneNumber': phone_number,
            'text': txt,
        }

        req = urllib.request.Request(self.ussd_url)
        req.method = 'POST'
        data_str = urllib.parse.urlencode(data)
        data_bytes = data_str.encode('utf-8')
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        req.data = data_bytes

        return req


    def _queue_user(self, i, u, tags=[]):
        iu = ImportUser(self.dh, u, self.chain_spec, self.source_chain_spec)
        self.dh.add(None, iu.original_address, 'ussd_phone')


    # Add all source users to lookup processing directory.
    # It is the responsiblity of the importer in the deferred syncer to call the parent prepare.
    # The parent prepare is not needed for this phase since we are only using src and custom stores.
    def prepare(self):
        need_init = False
        try:
            os.stat(self.dh.path('.complete', 'ussd_phone'))
        except FileNotFoundError:
            need_init = True

        if need_init:
            self.walk(self._queue_user)
            fp = self.dh.path('.complete', 'ussd_phone')
            f = open(fp, 'w')
            f.close()


    # create account is simply a matter of selecting the language on the menu.
    # TODO: add language preference data to imports generation, and already "import" the language in this step.
    def create_account(self, i, u):
        phone_number = phone_number_to_e164(u.tel, None)
        req = self._build_ussd_request(
                             phone_number,
                             self.ussd_service_code,
                             )
        logg.debug('ussd request: {} {}'.format(req.full_url, req.data))
        response = urllib.request.urlopen(req)
        response_data = response.read().decode('utf-8')
        logg.debug('ussd response: {}'.format(responsee_data))

        req = self._build_ussd_request(
                             phone_number,
                             self.ussd_service_code,
                             txt='1',
                             )
        logg.debug('ussd request: {} {}'.format(req.full_url, req.data))
        response = urllib.request.urlopen(req)
        response_data = response.read().decode('utf-8')
        logg.debug('ussd response: {}'.format(responsee_data))


    # Retrieves user account registrations.
    # Creates and stores (queues) single-tx block records for each one.
    # Note that it will store ANY account registration, whether or not it belongs to this import session.
    def filter(self, conn, block, tx, db_session):
        # get user if matching tx
        address = self._address_by_tx(tx)
        if address == None:
            return

        tampered_block = TamperedBlock(block.src(), tx)
        self.dh.add(address, tampered_block.src(), 'ussd_tx_src')
