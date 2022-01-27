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
from cic_seeding.filter import split_filter
from cic_seeding.chain import (
        set_chain_address,
        get_chain_addresses,
        )
from cic_seeding.legacy import (
        legacy_normalize_address,
        legacy_link_data,
        )

logg = logging.getLogger(__name__)


class Importer:

    def __init__(self, config, stores={}, default_tag=[]):
        self.chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
        self.source_chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC_SOURCE'))

        self.stores = {}
        self.stores['tags'] = AddressIndex(value_filter=split_filter, name='tags index')
        self.dh = DirHandler(config.get('_USERDIR'), stores=stores, exist_ok=True)
        try:
            reset = config.get('_RESET')
            self.dh.initialize_dirs(reset=config.get('_RESET'))
        except KeyError:
            pass
        self.default_tag = default_tag
    
        tags_path = self.dh.path(None, 'tags')

        try:
            self.stores['tags'].add_from_file(tags_path)
        except TypeError:
            pass

    def prepare(self):
        pass


    def filter(self, conn, block, tx, db_session):
        return self.filter(conn, block, tx, db_session=db_session)


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
