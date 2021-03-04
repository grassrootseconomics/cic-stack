# standard imports
import datetime

# external imports
import celery

# local imports
from cic_eth.db.models.debug import Debug
from cic_eth.db.models.base import SessionBase
from cic_eth.task import CriticalSQLAlchemyTask

celery_app = celery.current_app


@celery_app.task(base=CriticalSQLAlchemyTask)
def alert(chained_input, tag, txt):
    session = SessionBase.create_session()

    o = Debug(tag, txt)
    session.add(o)
    session.commit()

    session.close()
    
    return chained_input
