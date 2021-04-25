# standard imports
import sys
import os
import logging
import json

# external imports
import celery
import confini

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
            logg.debug('obj {} attrs'.format(obj.id))
            return obj.queue


def main():
    api = Api(
        config.get('CIC_CHAIN_SPEC'),
        queue='cic-eth',
        #callback_param='{}:{}:{}:{}'.format(args.redis_host_callback, args.redis_port_callback, redis_db, redis_channel),
        #callback_task='cic_eth.callbacks.redis.redis',
        #callback_queue=args.q,
        )
    t = api.create_account(register=False)
    for e in t.collect():
        print(e[0].backend.get('celery-task-meta-{}'.format(e[0].id)))
        print(e[0].name)
    #t.build_graph(intermediate=True, formatter=Fmtr()).to_dot(sys.stdout)ka
    #v = celery_app.control.inspect().query_task(t.id).objgraph()
    #v = celery_app.control.inspect().stats()


if __name__ == '__main__':
    main()
