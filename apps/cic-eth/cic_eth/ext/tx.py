# standard imports
import logging
import math

# third-pary imports
import celery
import moolb
from chainlib.chain import ChainSpec
from chainlib.connection import RPCConnection
from chainlib.eth.tx import (
        unpack,
        transaction_by_block,
        receipt,
        )
from chainlib.eth.block import block_by_number
from chainlib.eth.contract import abi_decode_single
from chainlib.eth.erc20 import ERC20
from hexathon import strip_0x
from cic_eth_registry import CICRegistry
from cic_eth_registry.erc20 import ERC20Token
from chainqueue.db.models.otx import Otx
from chainqueue.db.enum import StatusEnum
from chainqueue.query import get_tx_cache

# local imports
from cic_eth.queue.time import tx_times
from cic_eth.task import BaseTask
from cic_eth.db.models.base import SessionBase

celery_app = celery.current_app
logg = logging.getLogger()

MAX_BLOCK_TX = 250


# TODO: Make this method easier to read
@celery_app.task(bind=True, base=BaseTask)
def list_tx_by_bloom(self, bloomspec, address, chain_spec_dict):
    """Retrieve external transaction data matching the provided filter

    The bloom filter representation with the following structure (the size of the filter will be inferred from the size of the provided filter data):
        {
            'alg': <str; hashing algorithm, currently only "sha256" is understood>,
            'high': <number; highest block number in matched set>,
            'low': <number; lowest block number in matched set>,
            'filter_rounds': <number; hashing rounds used to generate filter entry>,
            'block_filter': <hex; bloom filter data with block matches>,
            'blocktx_filter': <hex; bloom filter data with block+tx matches>,
        }

    :param bloomspec: Bloom filter data
    :type bloomspec: dict (see description above)
    :param address: Recipient address to use in matching
    :type address: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: dict of transaction data as dict, keyed by transaction hash
    :rtype: dict of dict
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    chain_str = str(chain_spec)
    rpc = RPCConnection.connect(chain_spec, 'default')
    registry = CICRegistry(chain_spec, rpc)

    block_filter_data = bytes.fromhex(bloomspec['block_filter'])
    tx_filter_data = bytes.fromhex(bloomspec['blocktx_filter'])
    databitlen = len(block_filter_data)*8
    block_filter = moolb.Bloom(databitlen, bloomspec['filter_rounds'], default_data=block_filter_data)
    tx_filter = moolb.Bloom(databitlen, bloomspec['filter_rounds'], default_data=tx_filter_data)

    txs = {}
    for block_height in range(bloomspec['low'], bloomspec['high']):
        block_height_bytes = block_height.to_bytes(4, 'big')
        if block_filter.check(block_height_bytes):
            logg.debug('filter matched block {}'.format(block_height))
            o = block_by_number(block_height)
            block = rpc.do(o)
            logg.debug('block {}'.format(block))

            for tx_index in range(0, len(block['transactions'])):
                composite = tx_index + block_height
                tx_index_bytes = composite.to_bytes(4, 'big')
                if tx_filter.check(tx_index_bytes):
                    logg.debug('filter matched block {} tx {}'.format(block_height, tx_index))

                    try:
                        #tx = c.w3.eth.getTransactionByBlock(block_height, tx_index)
                        o = transaction_by_block(block['hash'], tx_index)
                        tx = rpc.do(o)
                    except Exception as e:
                        logg.debug('false positive on block {} tx {} ({})'.format(block_height, tx_index, e))
                        continue
                    tx_address = None
                    tx_token_value = 0
                    try:
                        transfer_data = ERC20.parse_transfer_request(tx['data'])
                        tx_address = transfer_data[0]
                        tx_token_value = transfer_data[1]
                    except ValueError:
                        logg.debug('not a transfer transaction, skipping {}'.format(tx))
                        continue
                    if address == tx_address:
                        status = StatusEnum.SENT
                        try:
                            o = receipt(tx['hash'])
                            rcpt = rpc.do(o)
                            if rcpt['status'] == 0:
                                pending = StatusEnum.REVERTED
                            else:
                                pending = StatusEnum.SUCCESS
                        except Exception as e:
                            logg.error('skipping receipt lookup for {}: {}'.format(tx['hash'], e))
                            pass

                        # TODO: pass through registry to validate declarator entry of token
                        #token = registry.by_address(tx['to'], sender_address=self.call_address)
                        token = ERC20Token(chain_spec, rpc, tx['to'])
                        token_symbol = token.symbol
                        token_decimals = token.decimals
                        times = tx_times(tx['hash'], chain_spec)
                        tx_r = {
                            'hash': tx['hash'],
                            'sender': tx['from'],
                            'recipient': tx_address,
                            'source_value': tx_token_value,
                            'destination_value': tx_token_value,
                            'source_token': tx['to'],
                            'destination_token': tx['to'],
                            'source_token_symbol': token_symbol,
                            'destination_token_symbol': token_symbol,
                            'source_token_decimals': token_decimals,
                            'destination_token_decimals': token_decimals,
                            'source_token_chain': chain_str,
                            'destination_token_chain': chain_str,
                            'nonce': tx['nonce'],
                                }
                        if times['queue'] != None:
                            tx_r['date_created'] = times['queue']
                        else:
                            tx_r['date_created'] = times['network']
                        txs[tx['hash']] = tx_r
                        break
    return txs


# TODO: Surely it must be possible to optimize this
# TODO: DRY this with callback filter in cic_eth/runnable/manager
# TODO: Remove redundant fields from end representation (timestamp, tx_hash)
@celery_app.task()
def tx_collate(tx_batches, chain_spec_dict, offset, limit, newest_first=True):
    """Merges transaction data from multiple sources and sorts them in chronological order.

    :param tx_batches: Transaction data inputs
    :type tx_batches: lists of lists of transaction data
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :param offset: Number of sorted results to skip (not yet implemented)
    :type offset: number
    :param limit: Maximum number of results to return (not yet implemented)
    :type limit: number
    :param newest_first: If True, returns results in reverse chronological order
    :type newest_first: bool
    :returns: Transactions
    :rtype: list
    """
    txs_by_block = {}
    chain_spec = ChainSpec.from_dict(chain_spec_dict)

    if isinstance(tx_batches, dict):
        tx_batches = [tx_batches]

    session = SessionBase.create_session()

    for b in tx_batches:
        for v in b.values():
            tx = None
            k = None
            try:
                hx = strip_0x(v)
                tx = unpack(bytes.fromhex(hx), chain_spec)
                txc = get_tx_cache(chain_spec, tx['hash'], session)
                txc['timestamp'] = int(txc['date_created'].timestamp())
                txc['hash'] = txc['tx_hash']
                tx = txc
            except TypeError:
                tx = v
                tx['timestamp'] = tx['date_created']
            k = '{}.{}.{}'.format(tx['timestamp'], tx['sender'], tx['nonce'])
            txs_by_block[k] = tx

    session.close()

    txs = []
    ks = list(txs_by_block.keys())
    ks.sort()
    if newest_first:
        ks.reverse()
    for k in ks:
        txs.append(txs_by_block[k])

    return txs
