# standard imports
import logging

# external imports
from chainlib.connection import (
        RPCConnection,
        ConnType,
        )
from chainlib.eth.connection import (
        EthUnixSignerConnection,
        EthHTTPSignerConnection,
        )
from chainlib.chain import ChainSpec

logg = logging.getLogger(__name__)


class RPC:

    def __init__(self, chain_spec, rpc_provider, signer_provider=None):
        self.chain_spec = chain_spec
        self.rpc_provider = rpc_provider
        self.signer_provider = signer_provider


    def get_default(self):
        return self.get_by_label('default')


    def get_by_label(self, label):
        return RPCConnection.connect(self.chain_spec, label)


    @staticmethod
    def from_config(config, use_signer=False, default_label='default', signer_label='signer'):
        chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

        RPCConnection.register_location(config.get('RPC_PROVIDER'), chain_spec, default_label)
        if use_signer:

            RPCConnection.register_constructor(ConnType.UNIX, EthUnixSignerConnection, signer_label)
            RPCConnection.register_constructor(ConnType.HTTP, EthHTTPSignerConnection, signer_label)
            RPCConnection.register_constructor(ConnType.HTTP_SSL, EthHTTPSignerConnection, signer_label)
            RPCConnection.register_location(config.get('SIGNER_PROVIDER'), chain_spec, signer_label) 
        rpc = RPC(chain_spec, config.get('RPC_PROVIDER'), signer_provider=config.get('SIGNER_PROVIDER'))
        logg.info('set up rpc: {}'.format(rpc))
        return rpc


    def __str__(self):
        return 'RPC factory, chain {}, rpc {}, signer {}'.format(self.chain_spec, self.rpc_provider, self.signer_provider)


# TOOD: re-implement file backend option from omittec code:
#broker = config.get('CELERY_BROKER_URL')
#if broker[:4] == 'file':
#    bq = tempfile.mkdtemp()
#    bp = tempfile.mkdtemp()
#    conf_update = {
#            'broker_url': broker,
#            'broker_transport_options': {
#                'data_folder_in': bq,
#                'data_folder_out': bq,
#                'data_folder_processed': bp,
#            },
#            }
#    if config.true('CELERY_DEBUG'):
#        conf_update['result_extended'] = True
#    current_app.conf.update(conf_update)
#    logg.warning('celery broker dirs queue i/o {} processed {}, will NOT be deleted on shutdown'.format(bq, bp))
#else:
#    conf_update = {
#            'broker_url': broker,
#            }
#    if config.true('CELERY_DEBUG'):
#        conf_update['result_extended'] = True
#    current_app.conf.update(conf_update)
#
#result = config.get('CELERY_RESULT_URL')
#if result[:4] == 'file':
#    rq = tempfile.mkdtemp()
#    current_app.conf.update({
#        'result_backend': 'file://{}'.format(rq),
#        })
#    logg.warning('celery backend store dir {} created, will NOT be deleted on shutdown'.format(rq))
#else:
#    current_app.conf.update({
#        'result_backend': result,
#        })
#
