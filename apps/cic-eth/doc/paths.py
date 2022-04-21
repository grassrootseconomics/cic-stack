# standard imports
import sys
import os
import logging
import json

# external imports
import celery
import confini
import celery.utils.graph

# local imports
from cic_eth.api import Api

logging.basicConfig(level=logging.DEBUG)
logg = logging.getLogger()


script_dir = os.path.realpath(os.path.dirname(__file__))
config_dir = os.path.join(script_dir, '..', 'config')
config = confini.Config(config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'), result_extended=True)


class Fmtr(celery.utils.graph.GraphFormatter):

    def label(self, obj):
        super(Fmtr, self).label(obj)
        if obj != None:
            if obj.name == None:
                raise RuntimeError('task name is not defined. Did you run celery with result_extended=True?')
            return obj.name


def main():
    api = Api(
        config.get('CHAIN_SPEC'),
        queue='cic-eth',
        #callback_param='{}:{}:{}:{}'.format(args.redis_host_callback, args.redis_port_callback, redis_db, redis_channel),
        #callback_task='cic_eth.callbacks.redis.redis',
        #callback_queue=args.q,
        )
    t = api.create_account(register=False)
    t.get_leaf()
    t.build_graph(intermediate=True, formatter=Fmtr()).to_dot(sys.stdout)


if __name__ == '__main__':
    main()
