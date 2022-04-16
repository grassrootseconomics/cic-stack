# standard imports
import logging

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db import dsn_from_config

logg = logging.getLogger(__name__)
logging.getLogger('chainlib').setLevel(logging.WARNING)


class AuditSession:

    def __init__(self, config, methods=[], conn=None):
        self.dirty = True
        self.dry_run = config.true('_DRY_RUN')
        self.methods = methods
        self.session = None
        self.rpc= None

        dsn = dsn_from_config(config)
        SessionBase.connect(dsn, 1)
        self.session = SessionBase.create_session()

        if config.true('_CHECK_RPC'):
            if conn == None:
                raise RuntimeError('check rpc is set, but no rpc connection exists')
            self.rpc = conn

        
    def __del__(self):
        if self.dirty:
            logg.warning('incomplete run so rolling back db calls')
            self.session.rollback()
        elif self.dry_run:
            logg.warning('dry run set so rolling back db calls')
            self.session.rollback()
        else:
            logg.info('committing database session')
            self.session.commit()
        self.session.close()


    def run(self):
        for m in self.methods:
            m(self.session, rpc=self.rpc, commit=bool(not self.dry_run))
        self.dirty = False
