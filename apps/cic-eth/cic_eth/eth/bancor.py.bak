# standard imports
import os
import logging

# third-party imports
import celery
import web3
from cic_registry import CICRegistry
from cic_registry.chain import ChainSpec

# local imports
from cic_eth.db import SessionBase
from cic_eth.db.models.convert import TxConvertTransfer
from cic_eth.db.models.otx import Otx
from cic_eth.db.models.tx import TxCache
from cic_eth.eth.task import sign_and_register_tx
from cic_eth.eth.task import create_check_gas_and_send_task
from cic_eth.eth.token import TokenTxFactory
from cic_eth.eth.factory import TxFactory
from cic_eth.eth.util import unpack_signed_raw_tx
from cic_eth.eth.rpc import RpcClient

celery_app = celery.current_app 
#logg = celery_app.log.get_default_logger()
logg = logging.getLogger()

contract_function_signatures = {
        'convert': 'f3898a97',
        'convert2': '569706eb',
        }


class BancorTxFactory(TxFactory):

    """Factory for creating Bancor network transactions.
    """
    def convert(
            self,
            source_token_address,
            destination_token_address,
            reserve_address,
            source_amount,
            minimum_return,
            chain_spec,
            fee_beneficiary='0x0000000000000000000000000000000000000000',
            fee_ppm=0,
            ):
        """Create a BancorNetwork "convert" transaction.

        :param source_token_address: ERC20 contract address for token to convert from
        :type source_token_address: str, 0x-hex
        :param destination_token_address: ERC20 contract address for token to convert to
        :type destination_token_address: str, 0x-hex
        :param reserve_address: ERC20 contract address of Common reserve token
        :type reserve_address: str, 0x-hex
        :param source_amount: Amount of source tokens to convert
        :type source_amount: int
        :param minimum_return: Minimum amount of destination tokens to accept as result for conversion
        :type source_amount: int
        :return: Unsigned "convert" transaction in standard Ethereum format
        :rtype: dict
        """
        network_contract = CICRegistry.get_contract(chain_spec, 'BancorNetwork')
        network_gas = network_contract.gas('convert')
        tx_convert_buildable = network_contract.contract.functions.convert2(
            [
                source_token_address,
                source_token_address,
                reserve_address,
                destination_token_address,
                destination_token_address,
            ],
            source_amount,
            minimum_return,
            fee_beneficiary,
            fee_ppm,
            )
        tx_convert = tx_convert_buildable.buildTransaction({
                'from': self.address,
                'gas': network_gas,
                'gasPrice': self.gas_price,
                'chainId': chain_spec.chain_id(),
                'nonce': self.next_nonce(),
                })
        return tx_convert


def unpack_convert(data):
    f = data[2:10]
    if f != contract_function_signatures['convert2']:
        raise ValueError('Invalid convert data ({})'.format(f))

    d = data[10:]
    path = d[384:]
    source = path[64-40:64]
    destination = path[-40:]

    amount = int(d[64:128], 16)
    min_return = int(d[128:192], 16)
    fee_recipient = d[192:256]
    fee = int(d[256:320], 16)
    return {
        'amount': amount,
        'min_return': min_return,
        'source_token': web3.Web3.toChecksumAddress('0x' + source),
        'destination_token': web3.Web3.toChecksumAddress('0x' + destination),
        'fee_recipient': fee_recipient,
        'fee': fee,
        }



# Kept for historical reference, it unpacks a convert call without fee parameters
#def _unpack_convert_mint(data):
#    f = data[2:10]
#    if f != contract_function_signatures['convert2']:
#        raise ValueError('Invalid convert data ({})'.format(f))
#
#    d = data[10:]
#    path = d[256:]
#    source = path[64-40:64]
#    destination = path[-40:]
#
#    amount = int(d[64:128], 16)
#    min_return = int(d[128:192], 16)
#    return {
#        'amount': amount,
#        'min_return': min_return,
#        'source_token': web3.Web3.toChecksumAddress('0x' + source),
#        'destination_token': web3.Web3.toChecksumAddress('0x' + destination),
#        }


@celery_app.task(bind=True)
def convert_with_default_reserve(self, tokens, from_address, source_amount, minimum_return, to_address, chain_str):
    """Performs a conversion between two liquid tokens using Bancor network.

    :param tokens: Token pair, source and destination respectively
    :type tokens: list of str, 0x-hex
    :param from_address: Ethereum address of sender
    :type from_address: str, 0x-hex
    :param source_amount: Amount of source tokens to convert
    :type source_amount: int
    :param minimum_return: Minimum about of destination tokens to receive
    :type minimum_return: int
    """

    chain_spec = ChainSpec.from_chain_str(chain_str)
    queue = self.request.delivery_info['routing_key']

    c = RpcClient(chain_spec, holder_address=from_address)

    cr = CICRegistry.get_contract(chain_spec, 'BancorNetwork')
    source_token = CICRegistry.get_address(chain_spec, tokens[0]['address'])
    reserve_address = CICRegistry.get_contract(chain_spec, 'BNTToken', 'ERC20').address()

    tx_factory = TokenTxFactory(from_address, c)
   
    tx_approve_zero = tx_factory.approve(source_token.address(), cr.address(), 0, chain_spec)
    (tx_approve_zero_hash_hex, tx_approve_zero_signed_hex) = sign_and_register_tx(tx_approve_zero, chain_str, queue, 'cic_eth.eth.token.otx_cache_approve') 

    tx_approve = tx_factory.approve(source_token.address(), cr.address(), source_amount, chain_spec)
    (tx_approve_hash_hex, tx_approve_signed_hex) = sign_and_register_tx(tx_approve, chain_str, queue, 'cic_eth.eth.token.otx_cache_approve') 

    tx_factory = BancorTxFactory(from_address, c)
    tx_convert = tx_factory.convert(
            tokens[0]['address'],
            tokens[1]['address'],
            reserve_address,
            source_amount,
            minimum_return,
            chain_spec,
            )
    (tx_convert_hash_hex, tx_convert_signed_hex) = sign_and_register_tx(tx_convert, chain_str, queue, 'cic_eth.eth.bancor.otx_cache_convert')

    # TODO: consider moving save recipient to async task / chain it before the tx send
    if to_address != None:
        save_convert_recipient(tx_convert_hash_hex, to_address, chain_str)

    s = create_check_gas_and_send_task(
            [tx_approve_zero_signed_hex, tx_approve_signed_hex, tx_convert_signed_hex],
            chain_str,
            from_address,
            tx_approve_zero['gasPrice'] * tx_approve_zero['gas'],
            tx_hashes_hex=[tx_approve_hash_hex],
            queue=queue,
            )
    s.apply_async()
    return tx_convert_hash_hex


#@celery_app.task()
#def process_approval(tx_hash_hex):
#    t = session.query(TxConvertTransfer).query(TxConvertTransfer.approve_tx_hash==tx_hash_hex).first()
#    c = session.query(Otx).query(Otx.tx_hash==t.convert_tx_hash)
#    gas_limit = 8000000
#    gas_price = GasOracle.gas_price()
#
#    # TODO: use celery group instead
#    s_queue = celery.signature(
#            'cic_eth.queue.tx.create',
#            [
#                nonce,
#                c['address'], # TODO: check that this is in fact sender address
#                c['tx_hash'],
#                c['signed_tx'],
#                ]
#            )
#    s_queue.apply_async()
#
#    s_check_gas = celery.signature(
#            'cic_eth.eth.tx.check_gas',
#            [
#                c['address'],
#                [c['signed_tx']],
#                gas_limit * gas_price,
#                ]
#            )
#    s_send = celery.signature(
#            'cic_eth.eth.tx.send',
#            [],
#            )
#
#    s_set_sent = celery.signature(
#            'cic_eth.queue.tx.set_sent_status',
#            [False],
#            )
#    s_send.link(s_set_sent)
#    s_check_gas.link(s_send)
#    s_check_gas.apply_async()
#    return tx_hash_hex



@celery_app.task()
def save_convert_recipient(convert_hash, recipient_address, chain_str):
    """Registers the recipient target for a convert-and-transfer operation.

    :param convert_hash: Transaction hash of convert operation
    :type convert_hash: str, 0x-hex
    :param recipient_address: Address of consequtive transfer recipient
    :type recipient_address: str, 0x-hex
    """
    session = SessionBase.create_session()
    t = TxConvertTransfer(convert_hash, recipient_address, chain_str)
    session.add(t)
    session.commit()
    session.close()


@celery_app.task()
def save_convert_transfer(convert_hash, transfer_hash):
    """Registers that the transfer part of a convert-and-transfer operation has been executed.

    :param convert_hash: Transaction hash of convert operation
    :type convert_hash: str, 0x-hex
    :param convert_hash: Transaction hash of transfer operation
    :type convert_hash: str, 0x-hex
    :returns: transfer_hash,
    :rtype: list, single str, 0x-hex
    """
    session = SessionBase.create_session()
    t = TxConvertTransfer.get(convert_hash)
    t.transfer(transfer_hash)
    session.add(t)
    session.commit()
    session.close()
    return [transfer_hash]


# TODO: seems unused, consider removing
@celery_app.task()
def resolve_converters_by_tokens(tokens, chain_str):
    """Return converters for a list of tokens.

    :param tokens: Token addresses to look up
    :type tokens: list of str, 0x-hex
    :return: Addresses of matching converters
    :rtype: list of str, 0x-hex
    """
    chain_spec = ChainSpec.from_chain_str(chain_str)
    for t in tokens:
        c = CICRegistry.get_contract(chain_spec, 'ConverterRegistry')
        fn = c.function('getConvertersByAnchors')
        try:
            converters = fn([t['address']]).call()
        except Exception as e:
            raise e
        t['converters'] = converters

    return tokens


@celery_app.task(bind=True)
def transfer_converted(self, tokens, holder_address, receiver_address, value, tx_convert_hash_hex, chain_str):
    """Execute the ERC20 transfer of a convert-and-transfer operation.

    First argument is a list of tokens, to enable the task to be chained to the symbol to token address resolver function. However, it accepts only one token as argument.

    :param tokens: Token addresses 
    :type tokens: list of str, 0x-hex
    :param holder_address: Token holder address
    :type holder_address: str, 0x-hex
    :param holder_address: Token receiver address
    :type holder_address: str, 0x-hex
    :param value: Amount of token, in 'wei'
    :type value: int
    :raises TokenCountError: Either none or more then one tokens have been passed as tokens argument
    :return: Transaction hash
    :rtype: str, 0x-hex
    """
    # we only allow one token, one transfer
    if len(tokens) != 1:
        raise TokenCountError

    chain_spec = ChainSpec.from_chain_str(chain_str)

    queue = self.request.delivery_info['routing_key']

    c = RpcClient(chain_spec, holder_address=holder_address)

    # get transaction parameters
    gas_price = c.gas_price()
    tx_factory = TokenTxFactory(holder_address, c)

    token_address = tokens[0]['address']
    tx_transfer = tx_factory.transfer(
        token_address,
        receiver_address,
        value,
        chain_spec,
            )
    (tx_transfer_hash_hex, tx_transfer_signed_hex) = sign_and_register_tx(tx_transfer, chain_str, queue, 'cic_eth.eth.token.otx_cache_transfer')

    # send transaction
    logg.info('transfer converted token {} from {} to {} value {} {}'.format(token_address, holder_address, receiver_address, value, tx_transfer_signed_hex))
    s = create_check_gas_and_send_task(
            [tx_transfer_signed_hex],
            chain_str,
            holder_address,
            tx_transfer['gasPrice'] * tx_transfer['gas'],
            None,
            queue,
            )
    s_save = celery.signature(
            'cic_eth.eth.bancor.save_convert_transfer',
            [
                tx_convert_hash_hex,
                tx_transfer_hash_hex,
                ],
            queue=queue,
            )
    s_save.link(s)
    s_save.apply_async()
    return tx_transfer_hash_hex


@celery_app.task()
def otx_cache_convert(
        tx_hash_hex,
        tx_signed_raw_hex,
        chain_str,
        ):

    chain_spec = ChainSpec.from_chain_str(chain_str)
    tx_signed_raw_bytes = bytes.fromhex(tx_signed_raw_hex[2:])
    tx = unpack_signed_raw_tx(tx_signed_raw_bytes, chain_spec.chain_id())
    tx_data = unpack_convert(tx['data'])
    logg.debug('tx data {}'.format(tx_data))

    session = TxCache.create_session()
    tx_cache = TxCache(
        tx_hash_hex,
        tx['from'],
        tx['from'],
        tx_data['source_token'],
        tx_data['destination_token'],
        tx_data['amount'],
        tx_data['amount'],
            )
    session.add(tx_cache)
    session.commit()
    session.close()
    return tx_hash_hex

