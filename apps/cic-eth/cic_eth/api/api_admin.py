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
from chainqueue.db.enum import (
        StatusEnum,
        StatusBits,
        is_alive,
        is_error_status,
        status_str,
    )
from chainqueue.error import TxStateChangeError

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.role import AccountRole
from cic_eth.db.models.nonce import Nonce
from cic_eth.error import InitializationError
from cic_eth.queue.query import get_tx

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


    def proxy_do(self, chain_spec, o):
        s_proxy = celery.signature(
                'cic_eth.task.rpc_proxy',
                [
                    chain_spec.asdict(),
                    o,
                    'default',
                    ],
                queue=self.queue
                )
        return s_proxy.apply_async()


    
    def registry(self):
        s_registry = celery.signature(
                'cic_eth.task.registry',
                [],
                queue=self.queue
                )
        return s_registry.apply_async()


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
            'cic_eth.queue.lock.get_lock',
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
            'cic_eth.queue.query.get_tx_cache',
            [
                chain_spec.asdict(),
                tx_hash_hex,
                ],
            queue=self.queue,
            )

        # TODO: This check should most likely be in resend task itself
        tx_dict = s_get_tx_cache.apply_async().get()
        if not is_alive(getattr(StatusEnum, tx_dict['status']).value):
            raise TxStateChangeError('Cannot resend mined or obsoleted transaction'.format(txold_hash_hex))
        
        if not in_place:
            raise NotImplementedError('resend as new not yet implemented')

        s = celery.signature(
            'cic_eth.eth.gas.resend_with_higher_gas',
            [
                chain_spec.asdict(),
                None,
                1.01,
                ],
            queue=self.queue,
            )

        s_manual = celery.signature(
            'cic_eth.queue.state.set_manual',
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
                'cic_eth.queue.query.get_account_tx',
                [
                    chain_spec.asdict(),
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
                    'cic_eth.queue.query.get_tx',
                    [
                    chain_spec.asdict(),
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
                logg.error('nonce gap; {} followed {} for account {}'.format(nonce_otx, last_nonce, tx['from']))
                blocking_tx = k
                blocking_nonce = nonce_otx
                break
            last_nonce = nonce_otx

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
                'cic_eth.queue.query.get_account_tx',
                [
                    chain_spec.asdict(),
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


    def account(self, chain_spec, address, include_sender=True, include_recipient=True, renderer=None, w=sys.stdout):
        """Lists locally originated transactions for the given Ethereum address.

        Performs a synchronous call to the Celery task responsible for performing the query.

        :param address: Ethereum address to return transactions for
        :type address: str, 0x-hex
        """
        last_nonce = -1
        s = celery.signature(
                'cic_eth.queue.query.get_account_tx',
                [
                    chain_spec.asdict(),
                    address,
                    ],
                queue=self.queue,
                )
        txs = s.apply_async().get()

        tx_dict_list = []
        for tx_hash in txs.keys():
            errors = []
            s = celery.signature(
                    'cic_eth.queue.query.get_tx_cache',
                    [
                        chain_spec.asdict(),
                        tx_hash,
                        ],
                    queue=self.queue,
                    )
            tx_dict = s.apply_async().get()
            if tx_dict['sender'] == address:
                if tx_dict['nonce'] - last_nonce > 1:
                    logg.error('nonce gap; {} followed {} for address {} tx {}'.format(tx_dict['nonce'], last_nonce, tx_dict['sender'], tx_hash))
                    errors.append('nonce')
                elif tx_dict['nonce'] == last_nonce:
                    logg.info('nonce {} duplicate for address {} in tx {}'.format(tx_dict['nonce'], tx_dict['sender'], tx_hash))
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
    # TODO: This method is WAY too long
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

        s = celery.signature(
            'cic_eth.queue.query.get_tx_cache',
            [
                chain_spec.asdict(),
                tx_hash,
                ],
            queue=self.queue,
            )
    
        t = s.apply_async()
        tx = t.get()
  
        source_token = None
        if tx['source_token'] != ZERO_ADDRESS:
            if registry != None:
                try:
                    source_token = registry.by_address(tx['source_token'])
                except UnknownContractError:
                    logg.warning('unknown source token contract {} (direct)'.format(tx['source_token']))
            else:
                s = celery.signature(
                        'cic_eth.task.registry_address_lookup',
                        [
                            chain_spec.asdict(),
                            tx['source_token'],
                            ],
                        queue=self.queue
                        )
                t = s.apply_async()
                source_token = t.get()
                if source_token == None:
                    logg.warning('unknown source token contract {} (task pool)'.format(tx['source_token']))


        destination_token = None
        if tx['destination_token'] != ZERO_ADDRESS:
            if registry != None:
                try:
                    destination_token = registry.by_address(tx['destination_token'])
                except UnknownContractError:
                    logg.warning('unknown destination token contract {}'.format(tx['destination_token']))
            else:
                s = celery.signature(
                        'cic_eth.task.registry_address_lookup',
                        [
                            chain_spec.asdict(),
                            tx['destination_token'],
                            ],
                        queue=self.queue
                        )
                t = s.apply_async()
                destination_token = t.get()
                if destination_token == None:
                    logg.warning('unknown destination token contract {} (task pool)'.format(tx['destination_token']))


        tx['sender_description'] = 'Custodial account'
        tx['recipient_description'] = 'Custodial account'

        o = code(tx['sender'])
        t = self.proxy_do(chain_spec, o)
        r = t.get()
        if len(strip_0x(r, allow_empty=True)) > 0:
            if registry != None:
                try:
                    sender_contract = registry.by_address(tx['sender'], sender_address=self.call_address)
                    tx['sender_description'] = 'Contract at {}'.format(tx['sender'])
                except UnknownContractError:
                    tx['sender_description'] = 'Unknown contract'
                except KeyError as e:
                    tx['sender_description'] = 'Unknown contract'
            else:
                s = celery.signature(
                        'cic_eth.task.registry_address_lookup',
                        [
                            chain_spec.asdict(),
                            tx['sender'],
                            ],
                        queue=self.queue
                        )
                t = s.apply_async()
                tx['sender_description'] = t.get()
                if tx['sender_description'] == None:
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
        t = self.proxy_do(chain_spec, o)
        r = t.get()
        if len(strip_0x(r, allow_empty=True)) > 0:
            if registry != None:
                try:
                    recipient_contract = registry.by_address(tx['recipient'])
                    tx['recipient_description'] = 'Contract at {}'.format(tx['recipient'])
                except UnknownContractError as e:
                    tx['recipient_description'] = 'Unknown contract'
                except KeyError as e:
                    tx['recipient_description'] = 'Unknown contract'
            else:
                s = celery.signature(
                        'cic_eth.task.registry_address_lookup',
                        [
                            chain_spec.asdict(),
                            tx['recipient'],
                            ],
                        queue=self.queue
                        )
                t = s.apply_async()
                tx['recipient_description'] = t.get()
                if tx['recipient_description'] == None:
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

        # TODO: this can mean either not subitted or culled, need to check other txs with same nonce to determine which
        tx['network_status'] = 'Not in node' 

        r = None
        try:
            o = transaction(tx_hash)
            t = self.proxy_do(chain_spec, o)
            r = t.get()
            if r != None:
                tx['network_status'] = 'Mempool'
        except Exception as e:
            logg.warning('(too permissive exception handler, please fix!) {}'.format(e))

        if r != None:
            try:
                o = receipt(tx_hash)
                t = self.proxy_do(chain_spec, o)
                r = t.get()
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
        t = self.proxy_do(chain_spec, o)
        r = t.get()
        tx['sender_gas_balance'] = r

        o = balance(tx['recipient'])
        t = self.proxy_do(chain_spec, o)
        r = t.get()
        tx['recipient_gas_balance'] = r

        tx_unpacked = unpack(bytes.fromhex(strip_0x(tx['signed_tx'])), chain_spec)
        tx['gas_price'] = tx_unpacked['gasPrice']
        tx['gas_limit'] = tx_unpacked['gas']
        tx['data'] = tx_unpacked['data']

        s = celery.signature(
            'cic_eth.queue.state.get_state_log',
            [
                chain_spec.asdict(),
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
