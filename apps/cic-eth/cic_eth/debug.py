# standard imports
import celery
import datetime

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db.models.debug import Debug

celery_app = celery.current_app


@celery_app.task()
def debug_add(tag, description):
    session = SessionBase.create_session()
    o = Debug(tag, description)
    o.date_created = datetime.datetime.utcnow()
    session.add(o)
    session.commit()
    session.close()
