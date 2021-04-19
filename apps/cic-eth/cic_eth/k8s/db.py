from cic_eth.db.models.base import SessionBase

def health():
    session = SessionBase.create_session()
    session.execute('SELECT count(*) from alembic_version')
    session.close()
    return True
