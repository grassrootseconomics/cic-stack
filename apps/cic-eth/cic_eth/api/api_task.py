"""API for cic-eth celery tasks

.. moduleauthor:: Louis Holbrook <dev@holbrook.no>

"""
# standard imports
import logging

# external imports 
import celery
from chainlib.chain import ChainSpec
from hexathon import strip_0x

# local imports
from cic_eth.api.base import ApiBase
from cic_eth.enum import LockEnum

app = celery.current_app

#logg = logging.getLogger(__name__)
logg = logging.getLogger()


class Api(ApiBase):

    @staticmethod
    def to_v_list(v, n):
        """Translate an arbitrary number of string and/or list arguments to a list of list of string arguments

        :param v: Arguments
        :type v: str or list
        :param n: Number of elements to generate arguments for
        :type n: int
        :rtype: list
        :returns: list of assembled arguments
        """
        if isinstance(v, str):
            vv = v
            v = []
            for i in range(n):
                v.append([vv])
        elif not isinstance(v, list):
            raise ValueError('argument must be single string, or list or strings or lists')
        else:
            if len(v) != n:
                raise ValueError('v argument count must match integer n')
            for i in range(n):
                if isinstance(v[i], str):
                    v[i] = [v[i]]
                elif not isinstance(v, list):
                    raise ValueError('proof argument must be single string, or list or strings or lists')

        return v
   

    def default_token(self):
        """Retrieves the default fallback token of the custodial network.

        :returns: uuid of root task
        :rtype: celery.Task
        """
        s_token = celery.signature(
                'cic_eth.eth.erc20.default_token',
                [],
                queue=self.queue,
                )
        if self.callback_param != None:
            s_token.link(self.callback_success)

        return s_token.apply_async()


    def token(self, token_symbol, proof=None):
        """Single-token alias for tokens method.

        See tokens method for details.

        :param token_symbol: Token symbol to look up
        :type token_symbol: str
        :param proof: Proofs to add to signature verification for the token
        :type proof: str or list
        :returns: uuid of root task
        :rtype: celery.Task
        """
        if not isinstance(token_symbol, str):
            raise ValueError('token symbol must be string')

        return self.tokens([token_symbol], proof=proof)


    def tokens(self, token_symbols, proof=None):
        """Perform a token data lookup from the token index. The token index will enforce unique associations between token symbol and contract address.

        Token symbols are always strings, and should be specified using uppercase letters.

        If the proof argument is included, the network will be queried for trusted signatures on the given proof(s). There must exist at least one trusted signature for every given proof for every token. Trusted signatures for the custodial system are provided at service startup.

        The proof argument may be specified in a number of ways:

        - as None, in which case proof checks are skipped (although there may still be builtin proof checks being performed)
        - as a single string, where the same proof is used for each token lookup
        - as an array of strings, where the respective proof is used for the respective token. number of proofs must match the number of tokens.
        - as an array of lists, where the respective proofs in each list is used for the respective token. number of lists of proofs must match the number of tokens.

        The success callback provided at the Api object instantiation will receive individual calls for each token that passes the proof checks. Each token that does not pass is passed to the Api error callback.

        This method is not intended to be used synchronously. Do so at your peril.

        :param token_symbols: Token symbol strings to look up
        :type token_symbol: list
        :param proof: Proof(s) to verify tokens against
        :type proof: None, str or list
        :returns: uuid of root task
        :rtype: celery.Task
        """
        if not isinstance(token_symbols, list):
            raise ValueError('token symbols argument must be list')

        if proof == None:
            logg.debug('looking up tokens without external proof check: {}'.format(','.join(token_symbols)))
            proof = ''

        logg.debug('proof is {}'.format(proof))
        l = len(token_symbols)
        if len(proof) == 0:
            l = 0 
        proof = Api.to_v_list(proof, l)

        chain_spec_dict = self.chain_spec.asdict()

        s_token_resolve = celery.signature(
                'cic_eth.eth.erc20.resolve_tokens_by_symbol',
                [
                    token_symbols,
                    chain_spec_dict,
                    ],
                queue=self.queue,
                )

        s_token_info = celery.signature(
                'cic_eth.eth.erc20.token_info',
                [
                    chain_spec_dict,
                    proof,
                    ],
                queue=self.queue,
                )

        s_token_verify = celery.signature(
                    'cic_eth.eth.erc20.verify_token_info',
                    [
                        chain_spec_dict,
                        self.callback_success,
                        self.callback_error,
                        ],
                    queue=self.queue,
                    )

        s_token_info.link(s_token_verify)
        s_token_resolve.link(s_token_info)
        return s_token_resolve.apply_async()


#    def convert_transfer(self, from_address, to_address, target_return, minimum_return, from_token_symbol, to_token_symbol):
#        """Executes a chain of celery tasks that performs conversion between two ERC20 tokens, and transfers to a specified receipient after convert has completed.
#
#        :param from_address: Ethereum address of sender
#        :type from_address: str, 0x-hex
#        :param to_address: Ethereum address of receipient
#        :type to_address: str, 0x-hex
#        :param target_return: Estimated return from conversion
#        :type  target_return: int
#        :param minimum_return: The least value of destination token return to allow
#        :type minimum_return: int
#        :param from_token_symbol: ERC20 token symbol of token being converted
#        :type from_token_symbol: str
#        :param to_token_symbol: ERC20 token symbol of token to receive
#        :type to_token_symbol: str
#        :returns: uuid of root task
#        :rtype: celery.Task
#        """
#        raise NotImplementedError('out of service until new DEX migration is done')
#        s_check = celery.signature(
#                'cic_eth.admin.ctrl.check_lock',
#                [
#                    [from_token_symbol, to_token_symbol],
#                    self.chain_spec.asdict(),
#                    LockEnum.QUEUE,
#                    from_address,
#                    ],
#                queue=self.queue,
#                )
#        s_nonce = celery.signature(
#                'cic_eth.eth.nonce.reserve_nonce',
#                [
#                    self.chain_spec.asdict(),
#                    ],
#                queue=self.queue,
#                )
#        s_tokens = celery.signature(
#                'cic_eth.eth.erc20.resolve_tokens_by_symbol',
#                [
#                    self.chain_str,
#                    ],
#                queue=self.queue,
#                )
#        s_convert = celery.signature(
#                'cic_eth.eth.bancor.convert_with_default_reserve',
#                [
#                    from_address,
#                    target_return,
#                    minimum_return,
#                    to_address,
#                    self.chain_spec.asdict(),
#                    ],
#                queue=self.queue,
#                )
#        s_nonce.link(s_tokens)
#        s_check.link(s_nonce)
#        if self.callback_param != None:
#            s_convert.link(self.callback_success)
#            s_tokens.link(s_convert).on_error(self.callback_error)
#        else:
#            s_tokens.link(s_convert)
#
#        t = s_check.apply_async(queue=self.queue)
#        return t
#
#
#    def convert(self, from_address, target_return, minimum_return, from_token_symbol, to_token_symbol):
#        """Executes a chain of celery tasks that performs conversion between two ERC20 tokens.
#
#        :param from_address: Ethereum address of sender
#        :type from_address: str, 0x-hex
#        :param target_return: Estimated return from conversion
#        :type  target_return: int
#        :param minimum_return: The least value of destination token return to allow
#        :type minimum_return: int
#        :param from_token_symbol: ERC20 token symbol of token being converted
#        :type from_token_symbol: str
#        :param to_token_symbol: ERC20 token symbol of token to receive
#        :type to_token_symbol: str
#        :returns: uuid of root task
#        :rtype: celery.Task
#        """
#        raise NotImplementedError('out of service until new DEX migration is done')
#        s_check = celery.signature(
#                'cic_eth.admin.ctrl.check_lock',
#                [
#                    [from_token_symbol, to_token_symbol],
#                    self.chain_spec.asdict(),
#                    LockEnum.QUEUE,
#                    from_address,
#                    ],
#                queue=self.queue,
#                )
#        s_nonce = celery.signature(
#                'cic_eth.eth.nonce.reserve_nonce',
#                [
#                    self.chain_spec.asdict(),
#                    ],
#                queue=self.queue,
#                )
#        s_tokens = celery.signature(
#                'cic_eth.eth.erc20.resolve_tokens_by_symbol',
#                [
#                    self.chain_spec.asdict(),
#                    ],
#                queue=self.queue,
#                )
#        s_convert = celery.signature(
#                'cic_eth.eth.bancor.convert_with_default_reserve',
#                [
#                    from_address,
#                    target_return,
#                    minimum_return,
#                    from_address,
#                    self.chain_spec.asdict(),
#                    ],
#                queue=self.queue,
#                )
#        s_nonce.link(s_tokens)
#        s_check.link(s_nonce)
#        if self.callback_param != None:
#            s_convert.link(self.callback_success)
#            s_tokens.link(s_convert).on_error(self.callback_error)
#        else:
#            s_tokens.link(s_convert)
#
#        t = s_check.apply_async(queue=self.queue)
#        return t


    def transfer_from(self, from_address, to_address, value, token_symbol, spender_address):
        """Executes a chain of celery tasks that performs a transfer of ERC20 tokens by one address on behalf of another address to a third party.

        :param from_address: Ethereum address of sender
        :type from_address: str, 0x-hex
        :param to_address: Ethereum address of recipient
        :type to_address: str, 0x-hex
        :param value: Estimated return from conversion
        :type  value: int
        :param token_symbol: ERC20 token symbol of token to send
        :type token_symbol: str
        :param spender_address: Ethereum address of recipient
        :type spender_address: str, 0x-hex
        :returns: uuid of root task
        :rtype: celery.Task
        """
        s_check = celery.signature(
                'cic_eth.admin.ctrl.check_lock',
                [
                    [token_symbol],
                    self.chain_spec.asdict(),
                    LockEnum.QUEUE,
                    from_address,
                    ],
                queue=self.queue,
                )
        s_nonce = celery.signature(
                'cic_eth.eth.nonce.reserve_nonce',
                [
                    self.chain_spec.asdict(),
                    from_address,
                    ],
                queue=self.queue,
                )
        s_tokens = celery.signature(
                'cic_eth.eth.erc20.resolve_tokens_by_symbol',
                [
                    self.chain_spec.asdict(),
                    ],
                queue=self.queue,
                )
        s_allow = celery.signature(
                'cic_eth.eth.erc20.check_allowance',
                [
                    from_address,
                    value,
                    self.chain_spec.asdict(),
                    spender_address,
                    ],
                queue=self.queue,
                )
        s_transfer = celery.signature(
                'cic_eth.eth.erc20.transfer_from',
                [
                    from_address,
                    to_address,
                    value,
                    self.chain_spec.asdict(),
                    spender_address,
                    ],
                queue=self.queue,
                )
        s_tokens.link(s_allow)
        s_nonce.link(s_tokens)
        s_check.link(s_nonce)
        if self.callback_param != None:
            s_transfer.link(self.callback_success)
            s_allow.link(s_transfer).on_error(self.callback_error)
        else:
            s_allow.link(s_transfer)

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
        #from_address = strip_0x(from_address)
        #to_address = strip_0x(to_address)
        s_check = celery.signature(
                'cic_eth.admin.ctrl.check_lock',
                [
                    [token_symbol],
                    self.chain_spec.asdict(),
                    LockEnum.QUEUE,
                    from_address,
                    ],
                queue=self.queue,
                )
        s_nonce = celery.signature(
                'cic_eth.eth.nonce.reserve_nonce',
                [
                    self.chain_spec.asdict(),
                    from_address,
                    ],
                queue=self.queue,
                )
        s_tokens = celery.signature(
                'cic_eth.eth.erc20.resolve_tokens_by_symbol',
                [
                    self.chain_spec.asdict(),
                    ],
                queue=self.queue,
                )
        s_transfer = celery.signature(
                'cic_eth.eth.erc20.transfer',
                [
                    from_address,
                    to_address,
                    value,
                    self.chain_spec.asdict(),
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
                'cic_eth.eth.erc20.resolve_tokens_by_symbol',
                [
                    [token_symbol],
                    self.chain_spec.asdict(),
                    ],
                queue=self.queue,
                )
        s_balance = celery.signature(
                'cic_eth.eth.erc20.balance',
                [
                    address,
                    self.chain_spec.asdict(),
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
                        self.chain_spec.asdict(),
                        ],
                    queue=self.queue,
                    )
            s_balance_outgoing = celery.signature(
                    'cic_eth.queue.balance.balance_outgoing',
                    [
                        address,
                        self.chain_spec.asdict(),
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
        else:
            # TODO: Chord is inefficient with only one chain, but assemble_balances must be able to handle different structures in order to avoid chord
            one = celery.chain(s_tokens, s_balance)
            if self.callback_param != None:
                s_result.link(self.callback_success).on_error(self.callback_error)
            t = celery.chord([one])(s_result)
    
        return t


    def create_account(self, password='', register=True):
        """Creates a new blockchain address encrypted with the given password, and calls the provided callback with the address of the new account.

        :param password: Password to encode the password with in the backend (careful, you will have to remember it)
        :type password: str
        :param register: Register the new account in accounts index backend
        :type register: bool
        :returns: uuid of root task
        :rtype: celery.Task
        """
        s_check = celery.signature(
                'cic_eth.admin.ctrl.check_lock',
                [
                    password,
                    self.chain_spec.asdict(),
                    LockEnum.CREATE,
                    ],
                queue=self.queue,
                )
        s_account = celery.signature(
                'cic_eth.eth.account.create',
                [
                    self.chain_spec.asdict(),
                    ],
                queue=self.queue,
                )
        s_check.link(s_account)
        if self.callback_param != None:
            s_account.link(self.callback_success)

        if register:
            s_nonce = celery.signature(
                'cic_eth.eth.nonce.reserve_nonce',
                [
                    self.chain_spec.asdict(),
                    'ACCOUNT_REGISTRY_WRITER',
                    ],
                queue=self.queue,
                )
            s_register = celery.signature(
                'cic_eth.eth.account.register', 
                [
                    self.chain_spec.asdict(),
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
                    self.chain_spec.asdict(),
                    LockEnum.QUEUE,
                    ],
                queue=self.queue,
                )
        s_nonce = celery.signature(
                'cic_eth.eth.nonce.reserve_nonce',
                [
                    self.chain_spec.asdict(),
                    'GAS_GIFTER',
                    ],
                queue=self.queue,
                )
        s_refill = celery.signature(
                'cic_eth.eth.gas.refill_gas',
                [
                    self.chain_spec.asdict(),
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
            'cic_eth.queue.query.get_account_tx',
            [
                self.chain_spec.asdict(),
                address,
                ],
            queue=self.queue,
            )

        s_brief = celery.signature(
            'cic_eth.ext.tx.tx_collate',
            [
                self.chain_spec.asdict(),
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
                    offset,
                    limit,
                    address,
                    ],
                queue=external_queue,
                )

            s_external_process = celery.signature(
                'cic_eth.ext.tx.list_tx_by_bloom',
                [
                    address,
                    self.chain_spec.asdict(),
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

