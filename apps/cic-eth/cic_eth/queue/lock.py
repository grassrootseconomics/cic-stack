# external imports
from chainqueue.db.models.otx import Otx
import celery

# local imports
from cic_eth.task import CriticalSQLAlchemyTask
from cic_eth.db import SessionBase
from cic_eth.db.models.lock import Lock


@celery_app.task(base=CriticalSQLAlchemyTask)
def get_lock(address=None):
    """Retrieve all active locks

    If address is set, the query will look up the lock for the specified address only. A list of zero or one elements is returned, depending on whether a lock is set or not.

    :param address: Get lock for only the specified address
    :type address: str, 0x-hex
    :returns: List of locks
    :rtype: list of dicts
    """
    session = SessionBase.create_session()
    q = session.query(
            Lock.date_created,
            Lock.address,
            Lock.flags,
            Otx.tx_hash,
            )
    q = q.join(Otx, isouter=True)
    if address != None:
        q = q.filter(Lock.address==address)
    else:
        q = q.order_by(Lock.date_created.asc())
   
    locks = []
    for lock in q.all():
        o = {
            'date': lock[0],
            'address': lock[1],
            'tx_hash': lock[3],
            'flags': lock[2],
            }
        locks.append(o)
    session.close()

    return locks
