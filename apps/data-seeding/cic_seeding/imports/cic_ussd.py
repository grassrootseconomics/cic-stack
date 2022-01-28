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


logg = logging.getLogger()


def _ussd_url(config):
    url_parts = urllib.parse.urlsplit(config.get('USSD_PROVIDER'))
    qs = urllib.parse.urlencode([
                ('username', config.get('USSD_USER')),
                ('password', config.get('USSD_PASS')),
            ]
            )
    url = urllib.parse.urlunsplit((url_parts[0], url_parts[1], url_parts[2], qs, '',))
    return str(url)


def _ussd_ssl(config):
    url_parts = urllib.parse.urlsplit(config.get('USSD_PROVIDER'))
    if url_parts[0] == 'https':
        return True
    return False


def default_req_factory(meta_url, ptr):
        url = urllib.parse.urljoin(meta_url, ptr)
        return urllib.request.Request(url=url)



class CicUssdConnectWorker(threading.Thread):

    req_factory = default_req_factory
    delay = 1
    max_tries = 0

    def __init__(self, importer, meta_url, job_queue):
        super(CicUssdConnectWorker, self).__init__()
        self.meta_url = meta_url
        self.imp = importer
        self.q = job_queue
   

    def run(self):
        while True:
            u = self.q.get()
            if u == None:
                return
            self.process(u)


    def process(self, u):
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

        self.imp.add(address, v, 'new')
        
        if self.q:
            self.q.put(None)


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


    def create_account(self, i, u):
        phone_number = phone_number_to_e164(u.tel, None)
        req = self._build_ussd_request(
                             phone_number,
                             self.ussd_service_code,
                             )
        logg.debug('sending to ussd endpoint {} {}'.format(req.full_url, req.data))
        response = urllib.request.urlopen(req)
        response_data = response.read().decode('utf-8')
        logg.debug(f'ussd response: {response_data[4:]}')

        req = self._build_ussd_request(
                             phone_number,
                             self.ussd_service_code,
                             txt='1',
                             )
        logg.debug('sending to ussd endpoint {} {}'.format(req.full_url, req.data))
        response = urllib.request.urlopen(req)
        response_data = response.read().decode('utf-8')
        logg.debug(f'ussd response: {response_data[4:]}')


    def process_user(self, i, u):
        self.create_account(i, u)
        return None


    def filter(self, conn, block, tx, db_session):
        # get user if matching tx
        address = self._address_by_tx(tx)
        if address == None:
            return

        serialized_block = self._export_user_block(address, block, tx)
        self.dh.add(address, serialized_block, 'ussd_tx_src')
