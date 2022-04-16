# standard imports
import logging
import sys
import os

# local imports
from cic_eth.db.models.base import SessionBase
from cic_eth.db import dsn_from_config

logg = logging.getLogger(__name__)
logging.getLogger('chainlib').setLevel(logging.WARNING)


class AuditSession:

    def __init__(self, config, conn=None):
        self.dirty = True
        self.dry_run = config.true('_DRY_RUN')
        self.methods = {}
        self.session = None
        self.rpc = None
        self.output_dir = config.get('_OUTPUT_DIR')
        self.f = None

        dsn = dsn_from_config(config)
        SessionBase.connect(dsn, 1)
        self.session = SessionBase.create_session()

        if config.true('_CHECK_RPC'):
            if conn == None:
                raise RuntimeError('check rpc is set, but no rpc connection exists')
            self.rpc = conn

        if self.output_dir != None:
            os.makedirs(self.output_dir)
       

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
        if self.f != None:
            self.f.close()


    def register(self, k, m):
        self.methods[k] = m
        logg.info('registered method {}'.format(k))


    def run(self):
        for k in self.methods.keys():
            logg.debug('running {}'.format(k))
            w = sys.stdout
            if self.output_dir != None:
                fp = os.path.join(self.output_dir, k)
                self.f = open(fp, 'w')
                w = self.f
            m = self.methods[k]
            m(self.session, rpc=self.rpc, commit=bool(not self.dry_run), w=w)

            if self.f != None:
                self.f.close()

            self.f = None

        self.dirty = False
