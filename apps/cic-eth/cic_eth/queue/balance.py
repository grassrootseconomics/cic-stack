# standard imports
import logging

# third-party imports
import celery
from chainlib.chain import ChainSpec
from hexathon import strip_0x
from chainqueue.db.models.otx import Otx
from chainqueue.db.models.tx import TxCache
from chainqueue.db.enum import (
        StatusBits,
        dead,
        )

# local imports
from cic_eth.db import SessionBase
from cic_eth.task import CriticalSQLAlchemyTask
from cic_eth.encode import tx_normalize

celery_app = celery.current_app

logg = logging.getLogger()


def __balance_outgoing_compatible(token_address, holder_address):
    token_address = tx_normalize.executable_address(token_address)
    holder_address = tx_normalize.wallet_address(holder_address)

    session = SessionBase.create_session()
    q = session.query(TxCache.from_value)
    q = q.join(Otx)
    q = q.filter(TxCache.sender==holder_address)
    status_compare = dead()
    q = q.filter(Otx.status.op('&')(status_compare)==0)
    q = q.filter(TxCache.source_token_address==token_address)
    delta = 0
    for r in q.all():
        delta += int(r[0])
    session.close()
    return delta


@celery_app.task(base=CriticalSQLAlchemyTask)
def balance_outgoing(tokens, holder_address, chain_spec_dict):
    """Retrieve accumulated value of unprocessed transactions sent from the given address.

    :param tokens: list of token spec dicts with addresses to retrieve balances for
    :type tokens: list of str, 0x-hex
    :param holder_address: Sender address
    :type holder_address: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Tokens dicts with outgoing balance added
    :rtype: dict
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    for t in tokens: 
        b = __balance_outgoing_compatible(t['address'], holder_address)
        t['balance_outgoing'] = b

    return tokens


def __balance_incoming_compatible(token_address, receiver_address):
    token_address = tx_normalize.executable_address(token_address)
    receiver_address = tx_normalize.wallet_address(receiver_address)

    session = SessionBase.create_session()
    q = session.query(TxCache.to_value)
    q = q.join(Otx)
    q = q.filter(TxCache.recipient==receiver_address)
    status_compare = dead()
    q = q.filter(Otx.status.op('&')(status_compare)==0)
    # TODO: this can change the result for the recipient if tx is later obsoleted and resubmission is delayed. 
    #q = q.filter(Otx.status.op('&')(StatusBits.IN_NETWORK)==StatusBits.IN_NETWORK)
    q = q.filter(TxCache.destination_token_address==token_address)
    delta = 0
    for r in q.all():
        delta += int(r[0])
    session.close()
    return delta


@celery_app.task(base=CriticalSQLAlchemyTask)
def balance_incoming(tokens, receipient_address, chain_spec_dict):
    """Retrieve accumulated value of unprocessed transactions to be received by the given address.

    :param tokens: list of token spec dicts with addresses to retrieve balances for
    :type tokens: list of str, 0x-hex
    :param holder_address: Recipient address
    :type holder_address: str, 0x-hex
    :param chain_str: Chain spec string representation
    :type chain_str: str
    :returns: Tokens dicts with outgoing balance added
    :rtype: dict
    """
    chain_spec = ChainSpec.from_dict(chain_spec_dict)
    for t in tokens: 
        b = __balance_incoming_compatible(t['address'], receipient_address)
        t['balance_incoming'] = b

    return tokens


@celery_app.task()
def assemble_balances(balances_collection):
    """Combines token spec dicts with individual balances into a single token spec dict.

    A "balance" means any field that is keyed with a string starting with "balance_"

    :param balances_collection: Token spec dicts
    :type balances_collection: list of lists of dicts
    :returns: Single token spec dict per token with all balances
    :rtype: list of dicts
    """
    tokens = {}
    logg.debug('received collection {}'.format(balances_collection))
    for c in balances_collection:
        for b in c:
            address = tx_normalize.executable_address(b['address'])
            if tokens.get(address) == None:
                tokens[address] = {
                    'address': address,
                    'converters': b['converters'],
                        }
            for k in b.keys():
                if k[:8] == 'balance_':
                    tokens[address][k] = b[k]
    return list(tokens.values())
