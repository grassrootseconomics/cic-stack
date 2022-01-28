# standard imports
import os
import logging
import json
import time
import phonenumbers
import sys

# external imports
from cic_types.models.person import Person
from cic_types.processor import generate_metadata_pointer
from cic_types import MetadataPointer
from chainlib.chain import ChainSpec

# local imports
from cic_seeding import DirHandler
from cic_seeding.index import AddressIndex
from cic_seeding.filter import (
        split_filter,
        remove_zeros_filter,
        )
from cic_seeding.chain import (
        set_chain_address,
        get_chain_addresses,
        )
from cic_seeding.legacy import (
        legacy_normalize_address,
        legacy_link_data,
        )

logg = logging.getLogger(__name__)


class ImportUser:

    def __init__(self, dirhandler, person, target_chain_spec, source_chain_spec, verify_address=None):
        self.person = person
        self.chain_spec = target_chain_spec
        self.source_chain_spec = source_chain_spec

        addresses = get_chain_addresses(person, target_chain_spec)
        if verify_address != None:
            if not is_same_address(verify_address, addresses[0]):
                raise ValueError('extracted adddress {} does not match verify adderss {}'.format(addresses[0], verify_address))
        self.address = addresses[0]

        original_addresses = get_chain_addresses(person, source_chain_spec)
        self.original_address = original_addresses[0]

        self.original_balance = self.original_token_balance(dirhandler)
    
        self.description = '{} {}@{} -> {}@{} original token balance {}'.format(
                self.person,
                self.original_address,
                self.source_chain_spec,
                self.address,
                self.chain_spec,
                self.original_balance,
                )


    def original_token_balance(self, dh):
        logg.debug('found original address {}@{} for {}'.format(self.original_address, self.source_chain_spec, self.person))
        balance = 0
        try:
            balance = dh.get(self.original_address, 'balances')
        except KeyError as e:
            logg.error('balance get fail for {}'.format(self))
            return
        return balance


    def __str__(self):
        return str(self.person)


class Importer:

    def __init__(self, config, stores={}, default_tag=[]):
        self.chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
        self.source_chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC_SOURCE'))

        self.stores = {}
        self.stores['tags'] = AddressIndex(value_filter=split_filter, name='tags index')
        self.stores['balances'] = AddressIndex(value_filter=remove_zeros_filter, name='balance index')

        for k in stores:
            self.stores[k] = stores[k]
       
        self.dh = DirHandler(config.get('_USERDIR'), stores=self.stores, exist_ok=True)
        try:
            reset = config.get('_RESET')
            self.dh.initialize_dirs(reset=config.true('_RESET'))
        except KeyError:
            logg.debug('whoa')
            pass
        self.default_tag = default_tag

        self.index_count = {}


    def user_by_address(self, address):
        j = self.dh.get(address, 'new')
        o = json.loads(j)
        person = Person.deserialize(o)
        return ImportUser(self.dh, person, self.chain_spec, self.source_chain_spec)


    def __len__(self):
        return self.index_count['balances']


    def prepare(self):
        for k in [
                'tags',
                'balances',
                ]:
            path = self.dh.path(None, k)
            c = self.stores[k].add_from_file(path)
            self.index_count[k] = c


    def filter(self, conn, block, tx, db_session):
        pass


    def process_user(self, i, u):
        raise NotImplementedError()


    def create_account(self, i, u):
        raise NotImplementedError()


    def process_user(self, i, u):
        address = self.create_account(i, u)
        logg.debug('[{}] register eth new address {} for {}'.format(i, address, u))
        return address


    def process_src(self, tags=[], batch_size=100, batch_delay=0.2):
        srcdir = self.dh.dirs.get('src')

        i = 0
        j = 0
        for x in os.walk(srcdir):
            for y in x[2]:
                s = None
                try:
                    s = self.dh.get(y, 'src')
                except ValueError:
                    continue
                o = json.loads(s)
                u = Person.deserialize(o)

                logg.debug('person {}'.format(u))

                # create new ethereum address (in custodial backend)
                new_address = self.process_user(i, u)

                
                # add address to identities in person object
                set_chain_address(u, self.chain_spec, new_address)


                # add updated person record to the migration data folder
                o = u.serialize()
                self.dh.add(new_address, json.dumps(o), 'new')


                new_address_clean = legacy_normalize_address(new_address)
                meta_key = generate_metadata_pointer(bytes.fromhex(new_address_clean), MetadataPointer.PERSON)
                self.dh.alias('new', 'meta', new_address_clean, alias_filename=new_address_clean + '.json', use_interface=False)

                phone_object = phonenumbers.parse(u.tel)
                phone = phonenumbers.format_number(phone_object, phonenumbers.PhoneNumberFormat.E164)
                meta_phone_key = generate_metadata_pointer(phone.encode('utf-8'), MetadataPointer.PHONE)


                self.dh.add(meta_phone_key, new_address_clean, 'phone')
                entry_path = self.dh.path(meta_phone_key, 'phone')
                legacy_link_data(entry_path)

                # custom data
                custom_key = generate_metadata_pointer(phone.encode('utf-8'), MetadataPointer.CUSTOM)
                
                old_addresses = get_chain_addresses(u, self.source_chain_spec)
                old_address = legacy_normalize_address(old_addresses[0])

                tag_data = self.dh.get(old_address, 'tags')

                for tag in self.default_tag:
                    tag_data.append(tag)

                for tag in tags:
                    tag_data.append(tag)

                self.dh.add(custom_key, json.dumps({'tags': tag_data}), 'custom')
                custom_path = self.dh.path(custom_key, 'custom')
                legacy_link_data(custom_path)

                i += 1
                sys.stdout.write('imported {} {}'.format(i, u).ljust(200) + "\r")
            
                j += 1
                if j == batch_size:
                    time.sleep(batch_delay)

    def process_target(self):
        pass
