# standard imports
import logging
import urllib.request
import urllib.parse
import urllib.error
import uuid
import os
import json
import threading
import time

# external imports
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
        #SeedQueue,
        normalize_key,
        )
from cic_seeding.sync import DeferredSyncQueue
from cic_seeding.chain import TamperedBlock
from cic_seeding.legacy import legacy_link_data

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
   

    # TODO: Add a quit channel!
    def run(self):
        i = 0
        while True:
            u = self.q.get()
            if u == None:
                logg.debug('queue returned none for worker {}'.format(self))
                time.sleep(0.1)
                continue
                #return
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
            except urllib.error.HTTPError as e:
                if self.max_tries > 0 and self.max_tries == tries:
                    raise RuntimeError('cannot find metadata resource {} -> {} ({})'.format(ph, self.ptr, e))
            except urllib.error.URLError as e:
                if self.max_tries > 0 and self.max_tries == tries:
                    raise RuntimeError('cannot access metadata endpoint {} -> {} ({})'.format(ph, self.ptr, e))

            logg.debug('metadata pointer {} not yet available for old address {}'.format(self.ptr, u.original_address))
            time.sleep(self.delay)
            
            #if r == None:
            #   continue
    
        logg.debug('have new address {} for phone {}'.format(address, ph))
        u.add_address(address)

        self.imp.dh.direct('set_have_address', 'ussd_tx_src', address)
        self.imp.dh.direct('next', 'ussd_phone', u.original_address)

        idx = float('{}.{}'.format(self.idx, i))
        self.imp.process_address(idx, u)

        self.imp.dh.direct('next', 'ussd_phone', u.original_address)


def apply_default_stores(config, semaphore, stores={}):
    store_path = os.path.join(config.get('_USERDIR'), 'ussd_tx_src')
    blocktx_store = DeferredSyncQueue(store_path, semaphore, key_normalizer=normalize_key)

    store_path = os.path.join(config.get('_USERDIR'), 'ussd_phone')
    unconnected_phone_store = AddressQueue(store_path)

    stores['ussd_tx_src'] = blocktx_store
    stores['ussd_phone'] = unconnected_phone_store

    return stores


# Links the user data in a separate directory for separate processing. (e.g. by CicUssdConnectWorker).
# Also provides the sync filter that stores block transactions for deferred processing.
class CicUssdImporter(Importer):

    def __init__(self, config, rpc, signer, signer_address, stores={}, default_tag=[], preferences={}):
        super(CicUssdImporter, self).__init__(config, rpc, signer=signer, signer_address=signer_address, stores=stores, default_tag=default_tag)

        self.preferences = preferences
        self.ussd_provider = config.get('USSD_PROVIDER')
        self.ussd_valid_service_codes = config.get('USSD_SERVICE_CODE').split(',')
        self.ussd_service_code = self.ussd_valid_service_codes[0]
        self.ussd_url = _ussd_url(config) 
        self.ussd_provider_ssl = _ussd_ssl(config)


    def _build_ussd_request(self, session_id, phone_number, service_code, txt=None):

        if txt is None:
            txt = ""
        data = {
            'sessionId': session_id,
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
        #self.dh.put(str(i), u.original_address, 'ussd_phone')
        self.dh.put(u.original_address, None, 'ussd_phone')


    # Add all source users to lookup processing directory.
    # It is the responsiblity of the importer in the deferred syncer to call the parent prepare.
    # The parent prepare is not needed for this phase since we are only using src and custom stores.
    def prepare(self):
        super(CicUssdImporter, self).prepare()
        need_init = False
        complete_fp = os.path.join(self.dh.user_dir, '.ussd_init_complete')
        try:
            os.stat(complete_fp)
        except FileNotFoundError:
            need_init = True

        if need_init:
            self.walk(self._queue_user)
            f = open(complete_fp, 'w')
            f.close()


    def create_account(self, i, u):
        session = uuid.uuid4().hex
        phone_number = phone_number_to_e164(u.phone, None)
        req = self._build_ussd_request(session, phone_number, self.ussd_service_code)
        logg.debug('ussd request: {} {}'.format(req.full_url, req.data))
        response = urllib.request.urlopen(req)
        response_data = response.read().decode('utf-8')
        logg.debug('ussd response: {}'.format(response_data))
        language_selection = '1' if self.preferences[phone_number] == 'en' else '2'
        attempts = 0
        while True:
            attempts += 1
            req = self._build_ussd_request( session, phone_number, self.ussd_service_code, txt=language_selection)
            logg.debug('ussd request: {} {}'.format(req.full_url, req.data))
            response = None
            try:
                response = urllib.request.urlopen(req)
            except urllib.error.HTTPError as e:
                if attempts is 5:
                    raise e
                if e.code >= 500:
                    time.sleep(0.3)
                    continue
                raise e
            response_data = response.read().decode('utf-8')
            logg.debug('ussd response: {}'.format(response_data))
            if len(response_data) < 3:
                raise RuntimeError('Unexpected response length')
            elif response_data[:3] == 'END':
                logg.debug('detected ussd END, so user should have been created now')
                break
            logg.debug('ussd response is still CON, retrying')
            time.sleep(0.1)


    def process_meta_custom_tags(self, i, u):
        super(CicUssdImporter, self).process_meta_custom_tags(i, u)
        phone = phonenumbers.format_number(u.phone, phonenumbers.PhoneNumberFormat.E164)
        custom_key = generate_metadata_pointer(phone.encode('utf-8'), MetadataPointer.CUSTOM)
        
        self.dh.put(custom_key, json.dumps({'tags': u.extra['tags']}), 'custom_phone')
        custom_path = self.dh.path(custom_key, 'custom')
        legacy_link_data(custom_path)


    # Retrieves user account registrations.
    # Creates and stores (queues) single-tx block records for each one.
    # Note that it will store ANY account registration, whether or not it belongs to this import session.
    def filter(self, conn, block, tx, db_session):
        # get user if matching tx
        address = self._address_by_tx(tx)
        if address == None:
            return

        tampered_block = TamperedBlock(block.src(), tx)
        self.dh.direct('set_have_block', 'ussd_tx_src', address, json.dumps(tampered_block.src()))
