# standard imports
import logging

# third-party imports
import celery
import web3
from cic_registry import zero_address
from cic_registry import zero_content
from cic_registry import CICRegistry
from crypto_dev_signer.eth.web3ext import Web3 as Web3Ext
from cic_registry.error import UnknownContractError

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.nonce import Nonce
from cic_eth.db.enum import StatusEnum
from cic_eth.error import InitializationError
from cic_eth.db.error import TxStateChangeError
from cic_eth.eth.rpc import RpcClient
from cic_eth.queue.tx import get_tx
from cic_eth.eth.util import unpack_signed_raw_tx

app = celery.current_app

#logg = logging.getLogger(__file__)
logg = logging.getLogger()


class AdminApi:
    """Provides an interface to view and manipulate existing transaction tasks and system runtime settings.

    :param rpc_client: Rpc client to use for blockchain connections.
    :type rpc_client: cic_eth.eth.rpc.RpcClient
    :param queue: Name of worker queue to submit tasks to
    :type queue: str
    """
    def __init__(self, rpc_client, queue='cic-eth'):
        self.rpc_client = rpc_client
        self.w3 = rpc_client.w3
        self.queue = queue


    def unlock(self, chain_spec, address, flags=None):
        s_unlock = celery.signature(
            'cic_eth.admin.ctrl.unlock',
            [
                str(chain_spec),
                flags,
                address,
                ],
            queue=self.queue,
            )
        return s_unlock.apply_async()


    def lock(self, chain_spec, address, flags=None):
        s_lock = celery.signature(
            'cic_eth.admin.ctrl.lock',
            [
                str(chain_spec),
                flags,
                address,
                ],
            queue=self.queue,
            )
        return s_lock.apply_async()


    def get_lock(self):
        s_lock = celery.signature(
            'cic_eth.queue.tx.get_lock',
            [],
            queue=self.queue,
            )
        return s_lock.apply_async().get()


    def tag_account(self, tag, address_hex):
        """Persistently associate an address with a plaintext tag.

        Some tags are known by the system and is used to resolve addresses to use for certain transactions. 

        :param tag: Address tag
        :type tag: str
        :param address_hex: Ethereum address to tag
        :type address_hex: str, 0x-hex
        :raises ValueError: Invalid checksum address
        """
        if not web3.Web3.isChecksumAddress(address_hex):
            raise ValueError('invalid address')
        session = SessionBase.create_session()
        role = AccountRole.set(tag, address_hex) 
        session.add(role)
        session.commit()
        session.close()


    def resend(self, tx_hash_hex, chain_str, in_place=True, unlock=False):
        logg.debug('resend {}'.format(tx_hash_hex))
        s_get_tx_cache = celery.signature(
            'cic_eth.queue.tx.get_tx_cache',
            [
                tx_hash_hex,
                ],
            queue=self.queue,
            )

        # TODO: This check should most likely be in resend task itself
        tx_dict = s_get_tx_cache.apply_async().get()
        if tx_dict['status'] in [StatusEnum.REVERTED, StatusEnum.SUCCESS, StatusEnum.CANCELLED, StatusEnum.OBSOLETED]: 
            raise TxStateChangeError('Cannot resend mined or obsoleted transaction'.format(txold_hash_hex))

        s = None
        if in_place:
            s = celery.signature(
                'cic_eth.eth.tx.resend_with_higher_gas',
                [
                    tx_hash_hex,
                    chain_str,
                    None,
                    1.01,
                    ],
                queue=self.queue,
                )
        else:
            raise NotImplementedError('resend as new not yet implemented')

        if unlock:
            s_gas = celery.signature(
                'cic_eth.admin.ctrl.unlock_send',
                [
                    chain_str,
                    tx_dict['sender'],
                ],
                queue=self.queue,
                )
            s.link(s_gas)

        return s.apply_async()
                        
    def check_nonce(self, address):
        s = celery.signature(
                'cic_eth.queue.tx.get_account_tx',
                [
                    address,
                    True,
                    False,
                    ],
                queue=self.queue,
                )
        txs = s.apply_async().get()

        blocking_tx = None
        blocking_nonce = None
        nonce_otx = 0
        for k in txs.keys():
            s_get_tx = celery.signature(
                    'cic_eth.queue.tx.get_tx',
                    [
                        k,
                        ],
                    queue=self.queue,
                    )
            tx = s_get_tx.apply_async().get()
            #tx = get_tx(k)
            logg.debug('checking nonce {}'.format(tx['nonce']))
            if tx['status'] in [StatusEnum.REJECTED, StatusEnum.FUBAR]:
                blocking_tx = k
                blocking_nonce = tx['nonce']
            nonce_otx = tx['nonce']

        #nonce_cache = Nonce.get(address)
        nonce_w3 = self.w3.eth.getTransactionCount(address, 'pending') 
        
        return {
            'nonce': {
                'network': nonce_w3,
                'queue': nonce_otx,
                #'cache': nonce_cache,
                'blocking': blocking_nonce,
            },
            'tx': {
                'blocking': blocking_tx,
                }
            }


    def fix_nonce(self, address, nonce):
        s = celery.signature(
                'cic_eth.queue.tx.get_account_tx',
                [
                    address,
                    True,
                    False,
                    ],
                queue=self.queue,
                )
        txs = s.apply_async().get()

        tx_hash_hex = None
        for k in txs.keys():
            tx_dict = get_tx(k)
            if tx_dict['nonce'] == nonce:
                tx_hash_hex = k

        s_nonce = celery.signature(
                'cic_eth.admin.nonce.shift_nonce',
                [
                    str(self.rpc_client.chain_spec),
                    tx_hash_hex, 
                ],
                queue=self.queue
                )
        return s_nonce.apply_async()


    # TODO: this is a stub, complete all checks
    def ready(self):
        """Checks whether all required initializations have been performed.

        :raises cic_eth.error.InitializationError: At least one setting pre-requisite has not been met.
        :raises KeyError: An address provided for initialization is not known by the keystore.
        """
        addr = AccountRole.get_address('ETH_GAS_PROVIDER_ADDRESS')
        if addr == zero_address:
            raise InitializationError('missing account ETH_GAS_PROVIDER_ADDRESS')

        self.w3.eth.sign(addr, text='666f6f')


    def account(self, chain_spec, address, cols=['tx_hash', 'sender', 'recipient', 'nonce', 'block', 'tx_index', 'status', 'network_status', 'date_created'], include_sender=True, include_recipient=True):
        """Lists locally originated transactions for the given Ethereum address.

        Performs a synchronous call to the Celery task responsible for performing the query.

        :param address: Ethereum address to return transactions for
        :type address: str, 0x-hex
        :param cols: Data columns to include
        :type cols: list of str
        """
        s = celery.signature(
                'cic_eth.queue.tx.get_account_tx',
                [address],
                queue=self.queue,
                )
        txs = s.apply_async().get()

        tx_dict_list = []
        for tx_hash in txs.keys():
            s = celery.signature(
                    'cic_eth.queue.tx.get_tx_cache',
                    [tx_hash],
                    queue=self.queue,
                    )
            tx_dict = s.apply_async().get()
            if tx_dict['sender'] == address and not include_sender:
                logg.debug('skipping sender tx {}'.format(tx_dict['tx_hash']))
                continue
            elif tx_dict['recipient'] == address and not include_recipient:
                logg.debug('skipping recipient tx {}'.format(tx_dict['tx_hash']))
                continue

            logg.debug(tx_dict)
            o = {
                'nonce': tx_dict['nonce'], 
                'tx_hash': tx_dict['tx_hash'],
                'status': tx_dict['status'],
                'date_updated': tx_dict['date_updated'],
                    }
            tx_dict_list.append(o)

        return tx_dict_list


    # TODO: Add exception upon non-existent tx aswell as invalid tx data to docstring 
    def tx(self, chain_spec, tx_hash=None, tx_raw=None):
        """Output local and network details about a given transaction with local origin.

        If the transaction hash is given, the raw trasnaction data will be retrieved from the local transaction queue backend. Otherwise the raw transaction data must be provided directly. Only one of transaction hash and transaction data can be passed.

        :param chain_spec: Chain spec of the transaction's chain context 
        :type chain_spec: cic_registry.chain.ChainSpec
        :param tx_hash: Transaction hash of transaction to parse and view
        :type tx_hash: str, 0x-hex
        :param tx_raw: Signed raw transaction data to parse and view
        :type tx_raw: str, 0x-hex
        :raises ValueError: Both tx_hash and tx_raw are passed
        :return: Transaction details
        :rtype: dict
        """
        if tx_hash != None and tx_raw != None:
            ValueError('Specify only one of hash or raw tx')

        if tx_raw != None:
            tx_hash = self.w3.keccak(hexstr=tx_raw).hex()

        s = celery.signature(
            'cic_eth.queue.tx.get_tx_cache',
            [tx_hash],
            queue=self.queue,
            )
    
        tx = s.apply_async().get()
  
        source_token = None
        if tx['source_token'] != zero_address:
            try:
                source_token = CICRegistry.get_address(chain_spec, tx['source_token']).contract
            except UnknownContractError:
                source_token_contract = self.w3.eth.contract(abi=CICRegistry.abi('ERC20'), address=tx['source_token'])
                source_token = CICRegistry.add_token(chain_spec, source_token_contract)
                logg.warning('unknown source token contract {}'.format(tx['source_token']))

        destination_token = None
        if tx['source_token'] != zero_address:
            try:
                destination_token = CICRegistry.get_address(chain_spec, tx['destination_token'])
            except UnknownContractError:
                destination_token_contract = self.w3.eth.contract(abi=CICRegistry.abi('ERC20'), address=tx['source_token'])
                destination_token = CICRegistry.add_token(chain_spec, destination_token_contract)
                logg.warning('unknown destination token contract {}'.format(tx['destination_token']))

        tx['sender_description'] = 'Custodial account'
        tx['recipient_description'] = 'Custodial account'

        c = RpcClient(chain_spec)
        if len(c.w3.eth.getCode(tx['sender'])) > 0:
            try:
                sender_contract = CICRegistry.get_address(chain_spec, tx['sender'])
                tx['sender_description'] = 'Contract {}'.format(sender_contract.identifier())
            except UnknownContractError:
                tx['sender_description'] = 'Unknown contract'
            except KeyError as e:
                tx['sender_description'] = 'Unknown contract'
        else:
            s = celery.signature(
                    'cic_eth.eth.account.have',
                    [
                        tx['sender'],
                        str(chain_spec),
                        ],
                    queue=self.queue,
                    )
            t = s.apply_async()
            account = t.get()
            if account == None:
                tx['sender_description'] = 'Unknown account'
            else:
                s = celery.signature(
                    'cic_eth.eth.account.role',
                    [
                        tx['sender'],
                        str(chain_spec),
                        ],
                    queue=self.queue,
                    )
                t = s.apply_async()
                role = t.get()
                if role != None:
                    tx['sender_description'] = role


        if len(c.w3.eth.getCode(tx['recipient'])) > 0:
            try:
                recipient_contract = CICRegistry.get_address(chain_spec, tx['recipient'])
                tx['recipient_description'] = 'Contract {}'.format(recipient_contract.identifier())
            except UnknownContractError as e:
                tx['recipient_description'] = 'Unknown contract'
            except KeyError as e:
                tx['recipient_description'] = 'Unknown contract'
        else:
            s = celery.signature(
                    'cic_eth.eth.account.have',
                    [
                        tx['recipient'],
                        str(chain_spec),
                        ],
                    queue=self.queue,
                    )
            t = s.apply_async()
            account = t.get()
            if account == None:
                tx['recipient_description'] = 'Unknown account'
            else:
                s = celery.signature(
                    'cic_eth.eth.account.role',
                    [
                        tx['recipient'],
                        str(chain_spec),
                        ],
                    queue=self.queue,
                    )
                t = s.apply_async()
                role = t.get()
                if role != None:
                    tx['recipient_description'] = role

        if source_token != None:
            tx['source_token_symbol'] = source_token.symbol()
            tx['sender_token_balance'] = source_token.function('balanceOf')(tx['sender']).call()

        if destination_token != None:
            tx['destination_token_symbol'] = destination_token.symbol()
            tx['recipient_token_balance'] = source_token.function('balanceOf')(tx['recipient']).call()

        tx['network_status'] = 'Not submitted'

        try:
            c.w3.eth.getTransaction(tx_hash)
            tx['network_status'] = 'Mempool'
        except web3.exceptions.TransactionNotFound:
            pass

        try:
            r = c.w3.eth.getTransactionReceipt(tx_hash)
            if r.status == 1:
                tx['network_status'] = 'Confirmed'
                tx['block'] = r.blockNumber
                tx['tx_index'] = r.transactionIndex
            else:
                tx['network_status'] = 'Reverted'
        except web3.exceptions.TransactionNotFound:
            pass

        tx['sender_gas_balance'] = c.w3.eth.getBalance(tx['sender'])
        tx['recipient_gas_balance'] = c.w3.eth.getBalance(tx['recipient'])

        tx_unpacked = unpack_signed_raw_tx(bytes.fromhex(tx['signed_tx'][2:]), chain_spec.chain_id())
        tx['gas_price'] = tx_unpacked['gasPrice']
        tx['gas_limit'] = tx_unpacked['gas']

        s = celery.signature(
            'cic_eth.queue.tx.get_state_log',
            [
                tx_hash,
                ],
            queue=self.queue,
            )
        t = s.apply_async()
        tx['status_log'] = t.get()

        return tx
