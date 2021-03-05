# standard imports
import logging

# third-party imports
import celery

# local imports
from cic_eth.eth.token import TokenTxFactory


logg = logging.getLogger()


def test_approve(
        init_rpc,
        default_chain_spec,
        celery_session_worker,
        bancor_tokens,
        bancor_registry,
        cic_registry,
        ):

    token_data = [
                    {
                        'address': bancor_tokens[0],
                    },
                    ]
    s_nonce = celery.signature(
            'cic_eth.eth.tx.reserve_nonce',
            [
                token_data,
                init_rpc.w3.eth.accounts[0],
                ],
            queue=None,
            )
    s_approve = celery.signature(
            'cic_eth.eth.token.approve',
            [
                init_rpc.w3.eth.accounts[0],
                init_rpc.w3.eth.accounts[1],
                1024,
                str(default_chain_spec),
                ],
            )
    s_nonce.link(s_approve)
    t = s_nonce.apply_async()
    t.get()
    for r in t.collect():
        logg.debug('result {}'.format(r))

    assert t.successful()
