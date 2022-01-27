# standard imports
import os
import shutil
import sys
import stat
import logging

# external imports
from leveldir.hex import HexDir
from hexathon import strip_0x

# local imports
from cic_seeding.index import AddressIndex

logg = logging.getLogger(__name__)


class DirHandler:

    __address_dirs = {
        'src': 20,
        'new': 20,
        'keystore': 20,
            }

    __hash_dirs = {
        'phone': 32,
        'meta': 32,   # pointers to entries in "
        'custom': 32, # tags
        'txs': 32,
        }

    __csv_indices = {
        'balances',
        'tags',
            }

    __key_descriptions = {
        'src': 'user entries to migrate',
        'new': 'user entries with new addresses',
        'phone': 'phone number content address to blockchain address association',
        'meta': 'blockchain address content address to metadata association',
        'custom': 'blockchain address content address to extended metadata association',
            }


    hexdir_level = 2

    def __init__(self, user_dir, stores={}, exist_ok=False):
        self.user_dir = user_dir
        self.append = exist_ok
        self.dirs = {}
        self.dirs['src'] = os.path.join(self.user_dir, 'src')
        os.makedirs(self.dirs['src'], exist_ok=True)
        self.__stores = stores


    # TODO: which of these are obsolete?
    # TODO: should they all perhaps |
    def initialize_dirs(self, reset=False, remove_src=False):
        self.dirs['new'] = os.path.join(self.user_dir, 'new')
        self.dirs['meta'] = os.path.join(self.user_dir, 'meta')
        self.dirs['custom'] = os.path.join(self.user_dir, 'custom')
        self.dirs['phone'] = os.path.join(self.user_dir, 'phone')
        #self.dirs['preferences'] = os.path.join(self.user_dir, 'preferences')
        self.dirs['txs'] = os.path.join(self.user_dir, 'txs')
        #self.dirs['keyfile'] = os.path.join(self.user_dir, 'keystore')
        #self.dirs['custom_new'] = os.path.join(self.dirs['custom'], 'new')
        #self.dirs['custom_meta'] = os.path.join(self.dirs['custom'], 'meta')
        #self.dirs['phone_meta'] = os.path.join(self.dirs['phone'], 'meta')
        #self.dirs['phone_new'] = os.path.join(self.dirs['phone'], 'new')
        #self.dirs['preferences_meta'] = os.path.join(self.dirs['preferences'], 'meta')
        #self.dirs['preferences_new'] = os.path.join(self.dirs['preferences'], 'new')
        self.dirs['keystore'] = os.path.join(self.user_dir, 'keystore')
        self.dirs['bak'] = os.path.join(self.user_dir, 'bak')

        self.interfaces = {}

        if reset:
            self.__reset(remove_src=remove_src)

        if not remove_src:
            self.__check()

        self.__build_dirs()
        self.__build_indices()
        self.__register_hex_dirs()
        self.__register_indices()


    def __check(self):
        if not self.append:
            try:
                os.stat(self.dirs['src'])
                raise FileExistsError('src directory exists and append not set')
            except FileNotFoundError:
                pass 


    def __reset(self, remove_src=False):
        for k in self.dirs:
            d = self.dirs[k]
            if k == 'bak':
                continue
            if k == 'src':
                if not remove_src:
                    continue
            shutil.rmtree(d, ignore_errors=True)
            logg.debug('removed existing directory {}'.format(d))

        if remove_src:
            for idx in self.__csv_indices:
                idx_path = os.path.join(self.user_dir, idx + '.csv')
                os.unlink(idx_path)
                logg.debug('removed index {}'.format(idx_path))

        try:
            os.makedirs(self.dirs['src'])
        except FileExistsError:
            pass

        try:
            os.makedirs(self.dirs['bak'])
        except FileExistsError:
            pass


    def alias(self, source, alias, source_filename, alias_filename=None, use_interface=True):
        if source not in self.dirs:
            raise ValueError('source "{}" not found'.format(source))
        if alias not in self.dirs:
            raise ValueError('alias "{}" not found'.format(source))

        if alias_filename == None:
            alias_filename = source_filename

        source_path = self.interfaces[source].path(source_filename)
        if use_interface:
            alias_path = self.interfaces[alias].path(alias_filename)
        else:
            alias_path = os.path.join(self.dirs[alias], alias_filename)
      
        source_path = os.path.realpath(source_path)

        os.makedirs(os.path.dirname(alias_path), exist_ok=True)
        os.symlink(source_path, alias_path)
        logg.debug('added alias {} -> {}: {} -> {}'.format(alias, source, alias_filename, source_filename))


    def __build_indices(self):
        for idx in self.__csv_indices:
            idx_path = os.path.join(self.user_dir, idx + '.csv')
            try: 
                os.stat(idx_path)
                continue
            except FileNotFoundError:
                pass

            f = open(idx_path, 'w')
            f.close()


    def __build_dirs(self):
        try:
            os.stat(self.dirs['src'])
        except FileNotFoundError:
            sys.stderr.write('no users to import. please run create_import_users.py first\n')
            sys.exit(1)

        mkdirs = self.__address_dirs | self.__hash_dirs
        for d in mkdirs.keys():
            os.makedirs(self.dirs[d], exist_ok=True)


    def __register_hex_dirs(self):
        for dirkey in self.__address_dirs:
            d = HexDirInterface(self.dirs[dirkey], 20)
            self.interfaces[dirkey] = d

        for dirkey in self.__hash_dirs:
            d = HexDirInterface(self.dirs[dirkey], 32)
            self.interfaces[dirkey] = d


    def __register_indices(self):
        for k in self.__csv_indices:
            fp = os.path.join(self.user_dir, k + '.csv')
            self.interfaces[k] = IndexInterface(fp, store=self.__stores.get(k))
        logg.debug('added index {}'.format(self.interfaces[k]))


    def add(self, k, v, dirkey):
        logg.debug('dh add {} {} {}'.format(k, v, dirkey))
        ifc = self.interfaces[dirkey]
        return ifc.add(k, v)


    def get(self, k, dirkey):
        ifc = self.interfaces[dirkey]
        return ifc.get(k)


    def path(self, k, dirkey):
        ifc = self.interfaces[dirkey]
        return ifc.path(k)


    def flush(self, interface=None):
        if interface != None:
            self.interfaces[interface].flush()
            return
        for ifc in self.interfaces.keys():
            self.interfaces[ifc].flush()


class HexDirInterface:

    levels = 2

    def __init__(self, path, key_length):
        self.dir = HexDir(path, key_length, levels=self.levels)
        self.key_length = key_length

    def add(self, k, v):
        k = strip_0x(k)
        kb = bytes.fromhex(k)
        v =  v.encode('utf-8')
        return self.dir.add(kb, v)


    def get(self, k):
        k = strip_0x(k)
        file_path = self.dir.to_filepath(k)
        f = open(file_path, 'r')
        v = f.read()
        f.close()
        return v


    def path(self, k):
        return self.dir.to_filepath(k)


    def flush(self):
        pass


class IndexInterface:

    def __init__(self, path, store=None):
        self.__path = path
        self.f = open(self.__path, 'a')
        self.store = store
        if self.store == None:
            self.store = AddressIndex() 


    def add(self, k, v):
        self.store.add(k, v)
        self.f.write(k + ',' + v + '\n')


    def get(self, k):
        return self.store.get(k)


    def path(self, k):
        return self.__path


    def flush(self):
        self.f.close()
        self.f = open(self.__path, 'a')


    def __del__(self):
        self.f.close()


    def __str__(self):
        return 'index interface with store {}'.format(self.store)
