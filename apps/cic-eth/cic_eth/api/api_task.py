"""API for cic-eth celery tasks

.. moduleauthor:: Louis Holbrook <dev@holbrook.no>

"""
# standard imports
import logging

# external imports 
import celery
#from cic_registry.chain import ChainSpec
from cic_registry import CICRegistry
from chainlib.chain import ChainSpec

# local imports
from cic_eth.eth.factory import TxFactory
from cic_eth.db.enum import LockEnum

app = celery.current_app

logg = logging.getLogger(__name__)


class Api:
    """Creates task chains to perform well-known CIC operations.

    Each method that sends tasks returns details about the root task. The root task uuid can be provided in the callback, to enable to caller to correlate the result with individual calls. It can also be used to independently poll the completion of a task chain.

    :param callback_param: Static value to pass to callback
    :type callback_param: str
    :param callback_task: Callback task that executes callback_param call. (Must be included by the celery worker)
    :type callback_task: string
    :param queue: Name of worker queue to submit tasks to
    :type queue: str
    """
    def __init__(self, chain_str, queue='cic-eth', callback_param=None, callback_task='cic_eth.callbacks.noop.noop', callback_queue=None):
        self.chain_str = chain_str
        self.chain_spec = ChainSpec.from_chain_str(chain_str)
        self.callback_param = callback_param
        self.callback_task = callback_task
        self.queue = queue
        logg.info('api using queue {}'.format(self.queue))
        self.callback_success = None
        self.callback_error = None
        if callback_queue == None:
            callback_queue=self.queue

        if callback_param != None:
            self.callback_success = celery.signature(
                    callback_task,
                    [
                        callback_param,
                        0,
                        ],
                    queue=callback_queue,
                    )
            self.callback_error = celery.signature(
                    callback_task,
                    [
                        callback_param,
                        1,
                        ],
                    queue=callback_queue,
                    )       


    def convert_transfer(self, from_address, to_address, target_return, minimum_return, from_token_symbol, to_token_symbol):
        """Executes a chain of celery tasks that performs conversion between two ERC20 tokens, and transfers to a specified receipient after convert has completed.

        :param from_address: Ethereum address of sender
        :type from_address: str, 0x-hex
        :param to_address: Ethereum address of receipient
        :type to_address: str, 0x-hex
        :param target_return: Estimated return from conversion
        :type  target_return: int
        :param minimum_return: The least value of destination token return to allow
        :type minimum_return: int
        :param from_token_symbol: ERC20 token symbol of token being converted
        :type from_token_symbol: str
        :param to_token_symbol: ERC20 token symbol of token to receive
        :type to_token_symbol: str
        :returns: uuid of root task
        :rtype: celery.Task
        """
        s_check = celery.signature(
                'cic_eth.admin.ctrl.check_lock',
                [
                    [from_token_symbol, to_token_symbol],
                    self.chain_str,
                    LockEnum.QUEUE,
                    from_address,
                    ],
                queue=self.queue,
                )
        s_nonce = celery.signature(
                'cic_eth.eth.tx.reserve_nonce',
                [],
                queue=self.queue,
                )
        s_tokens = celery.signature(
                'cic_eth.eth.token.resolve_tokens_by_symbol',
                [
                    self.chain_str,
                    ],
                queue=self.queue,
                )
        s_convert = celery.signature(
                'cic_eth.eth.bancor.convert_with_default_reserve',
                [
                    from_address,
                    target_return,
                    minimum_return,
                    to_address,
                    self.chain_str,
                    ],
                queue=self.queue,
                )
        s_nonce.link(s_tokens)
        s_check.link(s_nonce)
        if self.callback_param != None:
            s_convert.link(self.callback_success)
            s_tokens.link(s_convert).on_error(self.callback_error)
        else:
            s_tokens.link(s_convert)

        t = s_check.apply_async(queue=self.queue)
        return t


    def convert(self, from_address, target_return, minimum_return, from_token_symbol, to_token_symbol):
        """Executes a chain of celery tasks that performs conversion between two ERC20 tokens.

        :param from_address: Ethereum address of sender
        :type from_address: str, 0x-hex
        :param target_return: Estimated return from conversion
        :type  target_return: int
        :param minimum_return: The least value of destination token return to allow
        :type minimum_return: int
        :param from_token_symbol: ERC20 token symbol of token being converted
        :type from_token_symbol: str
        :param to_token_symbol: ERC20 token symbol of token to receive
        :type to_token_symbol: str
        :returns: uuid of root task
        :rtype: celery.Task
        """
        s_check = celery.signature(
                'cic_eth.admin.ctrl.check_lock',
                [
                    [from_token_symbol, to_token_symbol],
                    self.chain_str,
                    LockEnum.QUEUE,
                    from_address,
                    ],
                queue=self.queue,
                )
        s_nonce = celery.signature(
                'cic_eth.eth.tx.reserve_nonce',
                [],
                queue=self.queue,
                )
        s_tokens = celery.signature(
                'cic_eth.eth.token.resolve_tokens_by_symbol',
                [
                    self.chain_str,
                    ],
                queue=self.queue,
                )
        s_convert = celery.signature(
                'cic_eth.eth.bancor.convert_with_default_reserve',
                [
                    from_address,
                    target_return,
                    minimum_return,
                    from_address,
                    self.chain_str,
                    ],
                queue=self.queue,
                )
        s_nonce.link(s_tokens)
        s_check.link(s_nonce)
        if self.callback_param != None:
            s_convert.link(self.callback_success)
            s_tokens.link(s_convert).on_error(self.callback_error)
        else:
            s_tokens.link(s_convert)

        t = s_check.apply_async(queue=self.queue)
        return t


    def transfer(self, from_address, to_address, value, token_symbol):
        """Executes a chain of celery tasks that performs a transfer of ERC20 tokens from one address to another.

        :param from_address: Ethereum address of sender
        :type from_address: str, 0x-hex
        :param to_address: Ethereum address of recipient
        :type to_address: str, 0x-hex
        :param value: Estimated return from conversion
        :type  value: int
        :param token_symbol: ERC20 token symbol of token to send
        :type token_symbol: str
        :returns: uuid of root task
        :rtype: celery.Task
        """
        s_check = celery.signature(
                'cic_eth.admin.ctrl.check_lock',
                [
                    [token_symbol],
                    self.chain_str,
                    LockEnum.QUEUE,
                    from_address,
                    ],
                queue=self.queue,
                )
        s_nonce = celery.signature(
                'cic_eth.eth.tx.reserve_nonce',
                [
                    from_address,
                    ],
                queue=self.queue,
                )
        s_tokens = celery.signature(
                'cic_eth.eth.token.resolve_tokens_by_symbol',
                [
                    self.chain_str,
                    ],
                queue=self.queue,
                )
        s_transfer = celery.signature(
                'cic_eth.eth.token.transfer',
                [
                    from_address,
                    to_address,
                    value,
                    self.chain_str,
                    ],
                queue=self.queue,
                )
        s_nonce.link(s_tokens)
        s_check.link(s_nonce)
        if self.callback_param != None:
            s_transfer.link(self.callback_success)
            s_tokens.link(s_transfer).on_error(self.callback_error)
        else:
            s_tokens.link(s_transfer)

        t = s_check.apply_async(queue=self.queue)
        return t


    def balance(self, address, token_symbol, include_pending=True):
        """Calls the provided callback with the current token balance of the given address.

        :param address: Ethereum address of holder
        :type address: str, 0x-hex
        :param token_symbol: ERC20 token symbol of token to send
        :type token_symbol: str
        :param include_pending: If set, will include transactions that have not yet been fully processed
        :type include_pending: bool
        :returns: uuid of root task
        :rtype: celery.Task
        """
        if self.callback_param == None:
            logg.warning('balance pointlessly called with no callback url')

        s_tokens = celery.signature(
                'cic_eth.eth.token.resolve_tokens_by_symbol',
                [
                    [token_symbol],
                    self.chain_str,
                    ],
                queue=self.queue,
                )
        s_balance = celery.signature(
                'cic_eth.eth.token.balance',
                [
                    address,
                    self.chain_str,
                    ],
                queue=self.queue,
                )
        s_result = celery.signature(
                'cic_eth.queue.balance.assemble_balances',
                [],
                queue=self.queue,
                )

        last_in_chain = s_balance
        if include_pending:
            s_balance_incoming = celery.signature(
                    'cic_eth.queue.balance.balance_incoming',
                    [
                        address,
                        self.chain_str,
                        ],
                    queue=self.queue,
                    )
            s_balance_outgoing = celery.signature(
                    'cic_eth.queue.balance.balance_outgoing',
                    [
                        address,
                        self.chain_str,
                        ],
                    queue=self.queue,
                    )
            s_balance.link(s_balance_incoming)
            s_balance_incoming.link(s_balance_outgoing)
            last_in_chain = s_balance_outgoing

        one = celery.chain(s_tokens, s_balance)
        two = celery.chain(s_tokens, s_balance_incoming)
        three = celery.chain(s_tokens, s_balance_outgoing)

        t = None
        if self.callback_param != None:
            s_result.link(self.callback_success).on_error(self.callback_error)
            t = celery.chord([one, two, three])(s_result)
        else:
            t = celery.chord([one, two, three])(s_result)
    
        return t


    def create_account(self, password='', register=True):
        """Creates a new blockchain address encrypted with the given password, and calls the provided callback with the address of the new account.

        :param password: Password to encode the password with in the backend (careful, you will have to remember it)
        :type password: str
        :param register: Register the new account in accounts index backend
        :type password: bool
        :returns: uuid of root task
        :rtype: celery.Task
        """
        s_check = celery.signature(
                'cic_eth.admin.ctrl.check_lock',
                [
                    password,
                    self.chain_str,
                    LockEnum.CREATE,
                    ],
                queue=self.queue,
                )
        s_nonce = celery.signature(
                'cic_eth.eth.tx.reserve_nonce',
                [],
                queue=self.queue,
                )
        s_account = celery.signature(
                'cic_eth.eth.account.create',
                [
                    self.chain_str,
                    ],
                queue=self.queue,
                )
        s_check.link(s_account)
        if self.callback_param != None:
            s_account.link(self.callback_success)

        if register:
            s_register = celery.signature(
                'cic_eth.eth.account.register', 
                [
                    self.chain_str,
                    ],
                queue=self.queue,
                )
            s_nonce.link(s_register)
            s_account.link(s_nonce)

        t = s_check.apply_async(queue=self.queue)
        return t


    def refill_gas(self, address):
        """Creates a new gas refill transaction with the registered gas provider address.

        :param address: Ethereum address to send gas tokens to.
        :type address: str
        :returns: uuid of root task
        :rtype: celery.Task
        """
        s_check = celery.signature(
                'cic_eth.admin.ctrl.check_lock',
                [
                    address,
                    self.chain_str,
                    LockEnum.QUEUE,
                    ],
                queue=self.queue,
                )
        s_nonce = celery.signature(
                'cic_eth.eth.tx.reserve_nonce',
                [],
                queue=self.queue,
                )
        s_refill = celery.signature(
                'cic_eth.eth.tx.refill_gas',
                [
                    self.chain_str,
                    ],
                queue=self.queue,
                )
        s_nonce.link(s_refill) 
        s_check.link(s_nonce)
        if self.callback_param != None:
            s_refill.link(self.callback_success)

        t = s_check.apply_async(queue=self.queue)
        return t


    def list(self, address, limit=10, external_task=None, external_queue=None):
        """Retrieve an aggregate list of latest transactions of internal and (optionally) external origin in reverse chronological order.

        The array of transactions returned have the same dict layout as those passed by the callback filter in cic_eth/runnable/manager

        If the external task is defined, this task will be used to query external transactions. If this is not defined, no external transactions will be included. The task must accept (offset, limit, address) as input parameters, and return a bloom filter that will be used to retrieve transaction data for the matching transactions. See cic_eth.ext.tx.list_tx_by_bloom for details on the bloom filter dat format.

        :param address: Ethereum address to list transactions for
        :type address: str, 0x-hex
        :param limit: Amount of results to return
        :type limit: number
        :param external_task: Celery task providing external transactions
        :type external_task: str
        :param external_queue: Celery task queue providing exernal transactions task
        :type external_queue: str
        :returns: List of transactions
        :rtype: list of dict
        """
        offset = 0
        s_local = celery.signature(
            'cic_eth.queue.tx.get_account_tx',
            [
                address,
                ],
            queue=self.queue,
            )

        s_brief = celery.signature(
            'cic_eth.ext.tx.tx_collate',
            [
                self.chain_str,
                offset,
                limit
                ],
            queue=self.queue,
            )
        s_local.link(s_brief)
        if self.callback_param != None:
            s_brief.link(self.callback_success).on_error(self.callback_error)

        t = None
        if external_task != None:
            s_external_get = celery.signature(
                external_task,
                [
                    address,
                    offset,
                    limit,
                    ],
                queue=external_queue,
                )

            s_external_process = celery.signature(
                'cic_eth.ext.tx.list_tx_by_bloom',
                [
                    address,
                    self.chain_str,
                    ],
                queue=self.queue,
                    )
            c = celery.chain(s_external_get, s_external_process)
            t = celery.chord([s_local, c])(s_brief)
        else:
            t = s_local.apply_async(queue=self.queue)

        return t

    def ping(self, r):
        """A noop callback ping for testing purposes.

        :returns: uuid of callback task
        :rtype: celery.Task
        """
        if self.callback_param == None:
            logg.warning('nothing to do')
            return None

        t = self.callback_success.apply_async([r])
        return t
