# standard imports
import logging
import sys

# external imports
import celery
from chainlib.eth.constant import (
        ZERO_ADDRESS,
        )
from cic_eth_registry import CICRegistry
from cic_eth_registry.error import UnknownContractError
from chainlib.eth.address import to_checksum_address
from chainlib.eth.contract import code
from chainlib.eth.tx import (
        transaction,
        receipt,
        unpack,
        )
from chainlib.hash import keccak256_hex_to_hex
from hexathon import (
        strip_0x,
        add_0x,
        )
from chainlib.eth.gas import balance

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.tx import TxCache
from cic_eth.db.models.nonce import Nonce
from cic_eth.db.enum import (
        StatusEnum,
        StatusBits,
        is_alive,
        is_error_status,
        status_str,
    )
from cic_eth.error import InitializationError
from cic_eth.db.error import TxStateChangeError
from cic_eth.queue.tx import get_tx

app = celery.current_app

#logg = logging.getLogger(__file__)
logg = logging.getLogger()

local_fail = StatusBits.LOCAL_ERROR | StatusBits.NODE_ERROR | StatusBits.UNKNOWN_ERROR


class AdminApi:
    """Provides an interface to view and manipulate existing transaction tasks and system runtime settings.

    :param rpc_client: Rpc client to use for blockchain connections.
    :type rpc_client: cic_eth.eth.rpc.RpcClient
    :param queue: Name of worker queue to submit tasks to
    :type queue: str
    """
    def __init__(self, rpc, queue='cic-eth', call_address=ZERO_ADDRESS):
        self.rpc = rpc
        self.queue = queue
        self.call_address = call_address


    def unlock(self, chain_spec, address, flags=None):
        s_unlock = celery.signature(
            'cic_eth.admin.ctrl.unlock',
            [
                None,
                chain_spec.asdict(),
                address,
                flags,
                ],
            queue=self.queue,
            )
        return s_unlock.apply_async()


    def lock(self, chain_spec, address, flags=None):
        s_lock = celery.signature(
            'cic_eth.admin.ctrl.lock',
            [
                None,
                chain_spec.asdict(),
                address,
                flags,
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
        return s_lock.apply_async()


    def tag_account(self, tag, address_hex, chain_spec):
        """Persistently associate an address with a plaintext tag.

        Some tags are known by the system and is used to resolve addresses to use for certain transactions. 

        :param tag: Address tag
        :type tag: str
        :param address_hex: Ethereum address to tag
        :type address_hex: str, 0x-hex
        :raises ValueError: Invalid checksum address
        """
        s_tag = celery.signature(
            'cic_eth.eth.account.set_role',
            [
                tag,
                address_hex,
                chain_spec.asdict(),
                ],
            queue=self.queue,
            )
        return s_tag.apply_async()


    def have_account(self, address_hex, chain_spec):
        s_have = celery.signature(
            'cic_eth.eth.account.have',
            [
                address_hex,
                chain_spec.asdict(),
                ],
            queue=self.queue,
            )
        return s_have.apply_async()


    def resend(self, tx_hash_hex, chain_spec, in_place=True, unlock=False):

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
        #if tx_dict['status'] in [StatusEnum.REVERTED, StatusEnum.SUCCESS, StatusEnum.CANCELLED, StatusEnum.OBSOLETED]: 
        if not is_alive(getattr(StatusEnum, tx_dict['status']).value):
            raise TxStateChangeError('Cannot resend mined or obsoleted transaction'.format(txold_hash_hex))
        
        if not in_place:
            raise NotImplementedError('resend as new not yet implemented')

        s = celery.signature(
            'cic_eth.eth.tx.resend_with_higher_gas',
            [
                chain_spec.asdict(),
                None,
                1.01,
                ],
            queue=self.queue,
            )

        s_manual = celery.signature(
            'cic_eth.queue.tx.set_manual',
            [
                tx_hash_hex,
                ],
            queue=self.queue,
            )
        s_manual.link(s)

        if unlock:
            s_gas = celery.signature(
                'cic_eth.admin.ctrl.unlock_send',
                [
                    chain_spec.asdict(),
                    tx_dict['sender'],
                ],
                queue=self.queue,
                )
            s.link(s_gas)

        return s_manual.apply_async()
                        
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
        last_nonce = -1
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
            logg.debug('checking nonce {} (previous {})'.format(tx['nonce'], last_nonce))
            nonce_otx = tx['nonce']
            if not is_alive(tx['status']) and tx['status'] & local_fail > 0:
                logg.info('permanently errored {} nonce {} status {}'.format(k, nonce_otx, status_str(tx['status'])))
                blocking_tx = k
                blocking_nonce = nonce_otx
            elif nonce_otx - last_nonce > 1:
                logg.error('nonce gap; {} followed {}'.format(nonce_otx, last_nonce))
                blocking_tx = k
                blocking_nonce = nonce_otx
                break
            last_nonce = nonce_otx

        #nonce_cache = Nonce.get(address)
        #nonce_w3 = self.w3.eth.getTransactionCount(address, 'pending') 
        
        return {
            'nonce': {
                #'network': nonce_cache,
                'queue': nonce_otx,
                #'cache': nonce_cache,
                'blocking': blocking_nonce,
            },
            'tx': {
                'blocking': blocking_tx,
                }
            }


    def fix_nonce(self, address, nonce, chain_spec):
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
                    self.rpc.chain_spec.asdict(),
                    tx_hash_hex, 
                ],
                queue=self.queue
                )
        return s_nonce.apply_async()


#    # TODO: this is a stub, complete all checks
#    def ready(self):
#        """Checks whether all required initializations have been performed.
#
#        :raises cic_eth.error.InitializationError: At least one setting pre-requisite has not been met.
#        :raises KeyError: An address provided for initialization is not known by the keystore.
#        """
#        addr = AccountRole.get_address('ETH_GAS_PROVIDER_ADDRESS')
#        if addr == ZERO_ADDRESS:
#            raise InitializationError('missing account ETH_GAS_PROVIDER_ADDRESS')
#
#        self.w3.eth.sign(addr, text='666f6f')


    def account(self, chain_spec, address, include_sender=True, include_recipient=True, renderer=None, w=sys.stdout):
        """Lists locally originated transactions for the given Ethereum address.

        Performs a synchronous call to the Celery task responsible for performing the query.

        :param address: Ethereum address to return transactions for
        :type address: str, 0x-hex
        """
        last_nonce = -1
        s = celery.signature(
                'cic_eth.queue.tx.get_account_tx',
                [
                    address,
                    ],
                queue=self.queue,
                )
        txs = s.apply_async().get()

        tx_dict_list = []
        for tx_hash in txs.keys():
            errors = []
            s = celery.signature(
                    'cic_eth.queue.tx.get_tx_cache',
                    [tx_hash],
                    queue=self.queue,
                    )
            tx_dict = s.apply_async().get()
            if tx_dict['sender'] == address:
                if tx_dict['nonce'] - last_nonce > 1:
                    logg.error('nonce gap; {} followed {} for tx {}'.format(tx_dict['nonce'], last_nonce, tx_dict['hash']))
                    errors.append('nonce')
                elif tx_dict['nonce'] == last_nonce:
                    logg.warning('nonce {} duplicate in tx {}'.format(tx_dict['nonce'], tx_dict['hash']))
                last_nonce = tx_dict['nonce']
                if not include_sender:
                    logg.debug('skipping sender tx {}'.format(tx_dict['tx_hash']))
                    continue
            elif tx_dict['recipient'] == address and not include_recipient:
                logg.debug('skipping recipient tx {}'.format(tx_dict['tx_hash']))
                continue

            o = {
                'nonce': tx_dict['nonce'], 
                'tx_hash': tx_dict['tx_hash'],
                'status': tx_dict['status'],
                'date_updated': tx_dict['date_updated'],
                'errors': errors,
                    }
            if renderer != None:
                r = renderer(o)
                w.write(r + '\n')
            else:
                tx_dict_list.append(o)

        return tx_dict_list


    # TODO: Add exception upon non-existent tx aswell as invalid tx data to docstring 
    def tx(self, chain_spec, tx_hash=None, tx_raw=None, registry=None, renderer=None, w=sys.stdout):
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
        problems = []

        if tx_hash != None and tx_raw != None:
            ValueError('Specify only one of hash or raw tx')

        if tx_raw != None:
            tx_hash = add_0x(keccak256_hex_to_hex(tx_raw))
            #tx_hash = self.w3.keccak(hexstr=tx_raw).hex()

        s = celery.signature(
            'cic_eth.queue.tx.get_tx_cache',
            [tx_hash],
            queue=self.queue,
            )
    
        tx = s.apply_async().get()
  
        source_token = None
        if tx['source_token'] != ZERO_ADDRESS:
            try:
                source_token = registry.by_address(tx['source_token'])
                #source_token = CICRegistry.get_address(chain_spec, tx['source_token']).contract
            except UnknownContractError:
                #source_token_contract = self.w3.eth.contract(abi=CICRegistry.abi('ERC20'), address=tx['source_token'])
                #source_token = CICRegistry.add_token(chain_spec, source_token_contract)
                logg.warning('unknown source token contract {}'.format(tx['source_token']))

        destination_token = None
        if tx['source_token'] != ZERO_ADDRESS:
            try:
                #destination_token = CICRegistry.get_address(chain_spec, tx['destination_token'])
                destination_token = registry.by_address(tx['destination_token'])
            except UnknownContractError:
                #destination_token_contract = self.w3.eth.contract(abi=CICRegistry.abi('ERC20'), address=tx['source_token'])
                #destination_token = CICRegistry.add_token(chain_spec, destination_token_contract)
                logg.warning('unknown destination token contract {}'.format(tx['destination_token']))

        tx['sender_description'] = 'Custodial account'
        tx['recipient_description'] = 'Custodial account'

        o = code(tx['sender'])
        r = self.rpc.do(o)
        if len(strip_0x(r, allow_empty=True)) > 0:
            try:
                #sender_contract = CICRegistry.get_address(chain_spec, tx['sender'])
                sender_contract = registry.by_address(tx['sender'], sender_address=self.call_address)
                tx['sender_description'] = 'Contract at {}'.format(tx['sender']) #sender_contract)
            except UnknownContractError:
                tx['sender_description'] = 'Unknown contract'
            except KeyError as e:
                tx['sender_description'] = 'Unknown contract'
        else:
            s = celery.signature(
                    'cic_eth.eth.account.have',
                    [
                        tx['sender'],
                        chain_spec.asdict(),
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
                        chain_spec.asdict(),
                        ],
                    queue=self.queue,
                    )
                t = s.apply_async()
                role = t.get()
                if role != None:
                    tx['sender_description'] = role

        o = code(tx['recipient'])
        r = self.rpc.do(o)
        if len(strip_0x(r, allow_empty=True)) > 0:
            try:
                #recipient_contract = CICRegistry.by_address(tx['recipient'])
                recipient_contract = registry.by_address(tx['recipient'])
                tx['recipient_description'] = 'Contract at {}'.format(tx['recipient']) #recipient_contract)
            except UnknownContractError as e:
                tx['recipient_description'] = 'Unknown contract'
            except KeyError as e:
                tx['recipient_description'] = 'Unknown contract'
        else:
            s = celery.signature(
                    'cic_eth.eth.account.have',
                    [
                        tx['recipient'],
                        chain_spec.asdict(),
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
                        chain_spec.asdict(),
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

        r = None
        try:
            o = transaction(tx_hash)
            r = self.rpc.do(o)
            if r != None:
                tx['network_status'] = 'Mempool'
        except Exception as e:
            logg.warning('(too permissive exception handler, please fix!) {}'.format(e))

        if r != None:
            try:
                o = receipt(tx_hash)
                r = self.rpc.do(o)
                logg.debug('h {} o {}'.format(tx_hash, o))
                if int(strip_0x(r['status'])) == 1:
                    tx['network_status'] = 'Confirmed'
                else:
                    tx['network_status'] = 'Reverted'
                tx['network_block_number'] = r.blockNumber
                tx['network_tx_index'] = r.transactionIndex
                if tx['block_number'] == None:
                    problems.append('Queue is missing block number {} for mined tx'.format(r.blockNumber))
            except Exception as e:
                logg.warning('too permissive exception handler, please fix!')
                pass

        o = balance(tx['sender'])
        r = self.rpc.do(o)
        tx['sender_gas_balance'] = r

        o = balance(tx['recipient'])
        r = self.rpc.do(o)
        tx['recipient_gas_balance'] = r

        tx_unpacked = unpack(bytes.fromhex(tx['signed_tx'][2:]), chain_spec.chain_id())
        tx['gas_price'] = tx_unpacked['gasPrice']
        tx['gas_limit'] = tx_unpacked['gas']
        tx['data'] = tx_unpacked['data']

        s = celery.signature(
            'cic_eth.queue.tx.get_state_log',
            [
                tx_hash,
                ],
            queue=self.queue,
            )
        t = s.apply_async()
        tx['status_log'] = t.get()

        if len(problems) > 0:
            sys.stderr.write('\n')
            for p in problems:
                sys.stderr.write('!!!{}\n'.format(p))

        if renderer == None:
            return tx

        r = renderer(tx)
        w.write(r + '\n')
        return None
