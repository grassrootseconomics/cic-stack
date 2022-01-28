# standard imports
import logging
import json

# external imports
from chainlib.eth.address import to_checksum_address
from hexathon import (
        add_0x,
        strip_0x,
        )
from funga.eth.keystore.keyfile import to_dict as to_keyfile_dict
from funga.eth.keystore.dict import DictKeystore
from chainlib.eth.gas import (
        RPCGasOracle,
        Gas,
        )
from chainlib.eth.nonce import RPCNonceOracle
from chainlib.status import Status as TxStatus
from chainlib.hash import keccak256_string_to_hex
from cic_types.models.person import Person
from eth_erc20 import ERC20
from chainlib.eth.error import RequestMismatchException
from erc20_faucet import Faucet
from eth_accounts_index import AccountsIndex

# local imports
from cic_seeding.imports import (
        Importer,
        ImportUser,
        )
from cic_seeding.chain import get_chain_addresses
from cic_seeding.legacy import (
        legacy_normalize_file_key,
        legacy_link_data,
        )

logg = logging.getLogger(__name__)


class EthImporter(Importer):

    account_index_add_signature = keccak256_string_to_hex('add(address)')[:8]

    def __init__(self, rpc, signer, signer_address, config, stores={}):
        super(EthImporter, self).__init__(config, rpc, stores=stores)
        self.keystore = DictKeystore()
        self.signer = signer
        self.signer_address = signer_address
        self.nonce_oracle = RPCNonceOracle(signer_address, rpc)
        self.token_address = None
        self.token_symbol = None
        self.gas_gift_amount = int(config.get('ETH_GAS_AMOUNT'))

        self.token_decimals = None
        self.token_multiplier = None


    def __register_account(self, address):
        gas_oracle = RPCGasOracle(self.rpc, code_callback=self.get_max_gas)
        c = AccountsIndex(self.chain_spec, signer=self.signer, nonce_oracle=self.nonce_oracle, gas_oracle=gas_oracle)
        #c = AccountsIndexAddressDeclarator(self.chain_spec, signer=self.signer, nonce_oracle=self.nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, o) = c.add(self.lookup.get('account_registry'), self.signer_address, address)
        self.rpc.do(o)

        # export tx
        self.__export_tx(tx_hash_hex, o['params'][0])

        return tx_hash_hex


    def __gift_gas(self, conn, user):
        gas_oracle = RPCGasOracle(self.rpc, code_callback=self.get_min_gas)
        c = Gas(self.chain_spec, signer=self.signer, nonce_oracle=self.nonce_oracle, gas_oracle=gas_oracle)
        (tx_hash_hex, o) = c.create(self.signer_address, user.address, self.gas_gift_amount)

        conn.do(o)

        # export tx
        self.__export_tx(tx_hash_hex, o['params'][0])

        logg.info('gas gift value {} submitted for {} tx {}'.format(self.gas_gift_amount, user, tx_hash_hex))

        return tx_hash_hex


    def __export_key(self, address):
        pk = self.keystore.get(address)
        keyfile_content = to_keyfile_dict(pk, 'foo')
        address_index = legacy_normalize_file_key(address)
        self.dh.add(address_index, json.dumps(keyfile_content), 'keystore')
        path = self.dh.path(address_index, 'keystore')
        legacy_link_data(path)

        return path


    def __export_tx(self, tx_hash, data):
        tx_hash_hex = strip_0x(tx_hash)
        tx_data = strip_0x(data)
        self.dh.add(tx_hash_hex, tx_data, 'txs')


    def create_account(self, i, u):
        # create new keypair
        address_hex = self.keystore.new()
        address = add_0x(to_checksum_address(address_hex))
    
        # add keypair to registry 
        tx_hash_hex = self.__register_account(address)

        # export private key to file
        path = self.__export_key(address)
        
        logg.info('[{}] register eth chain for {} tx {} keyfile {}'.format(i, u, tx_hash_hex, path))

        return address


    def __trigger_faucet(self, conn, user):
        #gas_oracle = RPCGasOracle(self.rpc, code_callback=Faucet.gas)
        gas_oracle = RPCGasOracle(self.rpc, code_callback=self.get_max_gas)
        faucet = Faucet(self.chain_spec, signer=self.signer, gas_oracle=gas_oracle, nonce_oracle=self.nonce_oracle)
        faucet_address = self.lookup.get('faucet')
        (tx_hash_hex, o) = faucet.give_to(faucet_address, self.signer_address, user.address)
        r = conn.do(o)
    
        # export tx
        self.__export_tx(tx_hash_hex, o['params'][0])

        logg.info('faucet trigger submitted for {} tx {}'.format(user, tx_hash_hex))

        return tx_hash_hex


    def __gift_tokens(self, conn, user):
        balance_full = user.original_balance * self.token_multiplier

        gas_oracle = RPCGasOracle(self.rpc, code_callback=self.get_max_gas)
        erc20 = ERC20(self.chain_spec, signer=self.signer, gas_oracle=gas_oracle, nonce_oracle=self.nonce_oracle)
        (tx_hash_hex, o) = erc20.transfer(self.token_address, self.signer_address, user.address, balance_full)
        r = conn.do(o)

        # export tx
        self.__export_tx(tx_hash_hex, o['params'][0])

        logg.info('token gift value {} submitted for {} tx {}'.format(balance_full, user, tx_hash_hex))

        return tx_hash_hex


    def __address_by_tx(self, tx):
        if tx.payload == None or len(tx.payload) == 0:
            return None

        r = None
        try:
            r = AccountsIndex.parse_add_request(tx.payload)
        except RequestMismatchException:
            return None
        address = r[0]

        if tx.status != TxStatus.SUCCESS:
            logg.warning('failed accounts index transaction for {}: {}'.format(address, tx.hash))
            return None

        logg.debug('account registry add match for {} in {}'.format(address, tx.hash))
        return address


    def __user_by_address(self, address):
        try:
            j = self.dh.get(address, 'new')
        except FileNotFoundError:
            logg.debug('skip tx with unknown recipient address {}'.format(address))
            return None

        o = json.loads(j)

        person = Person.deserialize(o)

        u = ImportUser(self.dh, person, self.chain_spec, self.source_chain_spec, verify_address=address)

        return u


    def filter(self, conn, block, tx, db_session):
        super(EthImporter, self).filter(conn, block, tx, db_session)

        # get user if matching tx
        address = self.__address_by_tx(tx) 
        if address == None:
            return
        u = self.__user_by_address(address)
        if u == None:
            logg.debug('no match in import data for address {}'.format(address))
            return
        logg.info('tx user match for ' + u.description)

        # transfer old balance
        self.__gift_tokens(conn, u)
        
        # run the faucet
        self.__trigger_faucet(conn, u)

        # gift gas
        self.__gift_gas(conn, u)
