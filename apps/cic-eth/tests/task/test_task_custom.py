# external imports
import celery
from chainqueue.db.models.otx import Otx
from chainqueue.enum import StatusBits


def test_task_check_gas_low(
        default_chain_spec,
        eth_rpc,
        eth_signer,
        init_database,
        agent_roles,
        celery_session_worker,
        ):

        s = celery.signature(
            'cic_eth.eth.tx.custom',
            [
                0,
                agent_roles['ALICE'],
                agent_roles['BOB'],
                42,
                'deadbeef',
                10000000,
                1000000,
                default_chain_spec.asdict(),
                ],
            queue=None,
                )
        t = s.apply_async()
        r = t.get_leaf()
        assert t.successful

        o = Otx.load(r, session=init_database)
        assert o.status == StatusBits.QUEUED
