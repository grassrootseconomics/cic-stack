# standard imports
import logging

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()


def do(token_pair, sender, recipient, sender_balance, aux, block_number, tx_index):
    """Defines the function signature for a traffic generator. The method itself only logs the input parameters.

    If the error position in the return tuple is not None, the calling code should consider the generation as failed, and not count it towards the limit of simultaneous traffic items that can be simultaneously in flight.

    If the task_id position in the return tuple is None, the calling code should interpret the traffic item to have been synchronously completed, and not count it towards the limit of simultaneous traffic items that can be simultaneously in flight.

    The balance element of the result is the balance dict passed as argument, with fields updated according to the expected delta as a result of the operation. However, in the event that the generator module dispatches an asynchronous event then there is no guarantee that this balance will actually be the correct result. The caller should take care to periodically re-sync balance from the upstream.

    :param token_pair: Source and destination tokens for the traffic item.
    :type token_pair: 2-element tuple with cic_registry.token.Token
    :param sender: Sender address
    :type sender: str, 0x-hex
    :param recipient: Recipient address
    :type recipient: str, 0x-hex
    :param sender_balance: Sender balance in full decimal resolution
    :type sender_balance: complex balance dict
    :param aux: Custom parameters defined by traffic generation client code
    :type aux: dict
    :param block_number: Syncer block number position at time of method call
    :type block_number: number
    :param tx_index: Syncer block transaction index position at time of method call
    :type tx_index: number
    :raises KeyError: Missing required aux element
    :returns: Exception|None, task_id|None and adjusted_sender_balance respectively
    :rtype: tuple
    """
    logg.debug('running {} {} {} {} {} {} {} {}'.format(__name__, token_pair, sender, recipient, sender_balance, aux, block_number, tx_index))

    return (None, None, sender_balance, )
