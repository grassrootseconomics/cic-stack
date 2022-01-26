# standard imports
import os
import sys
import json
import logging
import argparse
import uuid
import datetime
import time
import phonenumbers
from glob import glob

# external imports
import redis
import confini
import celery
from hexathon import (
        add_0x,
        strip_0x,
        )
from chainlib.eth.address import to_checksum_address
from cic_types.models.person import Person
from cic_eth.api.api_task import Api
from chainlib.chain import ChainSpec
from cic_types.processor import generate_metadata_pointer
from cic_types import MetadataPointer

# local imports
#from common.dirs import initialize_dirs
from cic_seeding import DirHandler
from cic_seeding.index import AddressIndex


logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(script_dir)
base_config_dir = os.path.join(root_dir, 'config')

argparser = argparse.ArgumentParser()
argparser.add_argument('-c', type=str, help='config override directory')
argparser.add_argument('-i', '--chain-spec', dest='i', type=str, help='Chain specification string')
argparser.add_argument('-f', action='store_true', help='force clear previous state')
argparser.add_argument('--old-chain-spec', type=str, dest='old_chain_spec', default='evm:foo:1:oldchain', help='chain spec')
argparser.add_argument('--redis-host', dest='redis_host', type=str, help='redis host to use for task submission')
argparser.add_argument('--redis-port', dest='redis_port', type=int, help='redis host to use for task submission')
argparser.add_argument('--redis-db', dest='redis_db', type=int, help='redis db to use for task submission and callback')
argparser.add_argument('--redis-host-callback', dest='redis_host_callback', default='localhost', type=str, help='redis host to use for callback')
argparser.add_argument('--redis-port-callback', dest='redis_port_callback', default=6379, type=int, help='redis port to use for callback')
argparser.add_argument('--batch-size', dest='batch_size', default=100, type=int, help='burst size of sending transactions to node') # batch size should be slightly below cumulative gas limit worth, eg 80000 gas txs with 8000000 limit is a bit less than 100 batch size
argparser.add_argument('--batch-delay', dest='batch_delay', default=2, type=int, help='seconds delay between batches')
argparser.add_argument('--timeout', default=60.0, type=float, help='Callback timeout')
argparser.add_argument('--default-tag', dest='default_tag', type=str, action='append', default=[],help='Default tag to add when tag is missing')
argparser.add_argument('--tag', dest='tag', type=str, action='append', default=[], help='Explicitly add given tag')
argparser.add_argument('-q', type=str, default='cic-eth', help='Task queue')
argparser.add_argument('-v', action='store_true', help='Be verbose')
argparser.add_argument('-vv', action='store_true', help='Be more verbose')
argparser.add_argument('user_dir', type=str, help='path to users export dir tree')
args = argparser.parse_args()

if args.v:
    logg.setLevel(logging.INFO)
elif args.vv:
    logg.setLevel(logging.DEBUG)

config = None
if args.c != None:
    config = confini.Config(base_config_dir, os.environ.get('CONFINI_ENV_PREFIX'), override_config_dir=args.c)
else:
    config = confini.Config(base_config_dir, os.environ.get('CONFINI_ENV_PREFIX'))
config.process()
args_override = {
        'CHAIN_SPEC': getattr(args, 'i'),
        'REDIS_HOST': getattr(args, 'redis_host'),
        'REDIS_PORT': getattr(args, 'redis_port'),
        'REDIS_DB': getattr(args, 'redis_db'),
        }
config.dict_override(args_override, 'cli')
config.add(args.user_dir, '_USERDIR', True)
logg.debug('config loaded:\n{}'.format(config))

celery_app = celery.Celery(broker=config.get('CELERY_BROKER_URL'), backend=config.get('CELERY_RESULT_URL'))

redis_host = config.get('REDIS_HOST')
redis_port = config.get('REDIS_PORT')
redis_db = config.get('REDIS_DB')
r = redis.Redis(redis_host, redis_port, redis_db)

ps = r.pubsub()


old_chain_spec = ChainSpec.from_chain_str(args.old_chain_spec)
old_chain_str = str(old_chain_spec)

chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))
chain_str = str(chain_spec)

batch_size = args.batch_size
batch_delay = args.batch_delay

dh = DirHandler(config.get('_USERDIR'), force_reset=args.f)
dh.initialize_dirs()
dh.alias('src', 'old')
dirs = dh.dirs


def register_eth(i, u):
    redis_channel = str(uuid.uuid4())
    ps.subscribe(redis_channel)
    #ps.get_message()
    api = Api(
        config.get('CHAIN_SPEC'),
        queue=args.q,
        callback_param='{}:{}:{}:{}'.format(args.redis_host_callback, args.redis_port_callback, redis_db, redis_channel),
        callback_task='cic_eth.callbacks.redis.redis',
        callback_queue=args.q,
        )
    t = api.create_account(register=True)
    logg.debug('register {} -> {}'.format(u, t))

    while True:
        ps.get_message()
        m = ps.get_message(timeout=args.timeout)
        address = None
        if m == None:
            logg.debug('message timeout')
            return
        if m['type'] == 'subscribe':
            logg.debug('skipping subscribe message')
            continue
        try:
            r = json.loads(m['data'])
            address = r['result']
            break
        except Exception as e:
            if m == None:
                logg.critical('empty response from redis callback (did the service crash?) {}'.format(e))
            else:
                logg.critical('unexpected response from redis callback: {} {}'.format(m, e))
            sys.exit(1)
        logg.debug('[{}] register eth {} {}'.format(i, u, address))

    return address
   

if __name__ == '__main__':

#    user_tags = {}
#    f = open(os.path.join(config.get('_USERDIR'), 'tags.csv'), 'r')
#    while True:
#        r = f.readline().rstrip()
#        if len(r) == 0:
#            break
#        (old_address, tags_csv) = r.split(':')
#        old_address = strip_0x(old_address)
#        old_address_tag_key = to_checksum_address(old_address)
#        user_tags[old_address_tag_key] = tags_csv.split(',')
#        logg.debug('read tags {} for old address {}'.format(user_tags[old_address_tag_key], old_address))
#
    def split_filter(v):
        return v.split(',')

    user_tags = AddressIndex(value_filter=split_filter)
    tags_path = dh.path(None, 'tags')
    user_tags.add_from_file(tags_path)


    i = 0
    j = 0

    for x in os.walk(dirs['old']):
        for y in x[2]:
            if y[len(y)-5:] != '.json':
                continue
            filepath = os.path.join(x[0], y)
            f = open(filepath, 'r')
            try:
                o = json.load(f)
            except json.decoder.JSONDecodeError as e:
                f.close()
                logg.error('load error for {}: {}'.format(y, e))
                continue
            f.close()
            logg.debug('deserializing {} {}'.format(filepath, o))
            u = Person.deserialize(o)

            new_address = register_eth(i, u)
            if u.identities.get('evm') == None:
                u.identities['evm'] = {}
            sub_chain_str = '{}:{}'.format(chain_spec.network_id(), chain_spec.common_name())
            u.identities['evm'][chain_spec.fork()] = {}
            u.identities['evm'][chain_spec.fork()][sub_chain_str] = [new_address]

            new_address_clean = strip_0x(new_address)
            filepath = os.path.join(
                    dirs['new'],
                    new_address_clean[:2].upper(),
                    new_address_clean[2:4].upper(),
                    new_address_clean.upper() + '.json',
                    )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            o = u.serialize()
            f = open(filepath, 'w')
            f.write(json.dumps(o))
            f.close()

            meta_key = generate_metadata_pointer(bytes.fromhex(new_address_clean), MetadataPointer.PERSON)
            meta_filepath = os.path.join(dirs['meta'], '{}.json'.format(new_address_clean.upper()))
            os.symlink(os.path.realpath(filepath), meta_filepath)

            phone_object = phonenumbers.parse(u.tel)
            phone = phonenumbers.format_number(phone_object, phonenumbers.PhoneNumberFormat.E164)
            meta_phone_key = generate_metadata_pointer(phone.encode('utf-8'), MetadataPointer.PHONE)
            meta_phone_filepath = os.path.join(dirs['phone'], 'meta', meta_phone_key)

            filepath = os.path.join(
                    dirs['phone'],
                    'new',
                    meta_phone_key[:2].upper(),
                    meta_phone_key[2:4].upper(),
                    meta_phone_key.upper(),
                    )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            f = open(filepath, 'w')
            f.write(to_checksum_address(new_address_clean))
            f.close()

            os.symlink(os.path.realpath(filepath), meta_phone_filepath)


            # custom data
            custom_key = generate_metadata_pointer(bytes.fromhex(new_address_clean), MetadataPointer.CUSTOM)
            custom_filepath = os.path.join(dirs['custom'], 'meta', custom_key)

            filepath = os.path.join(
                    dirs['custom'],
                    'new',
                    custom_key[:2].upper(),
                    custom_key[2:4].upper(),
                    custom_key.upper() + '.json',
                    )
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
           
            sub_old_chain_str = '{}:{}'.format(old_chain_spec.network_id(), old_chain_spec.common_name())
            logg.debug('u id {}'.format(u.identities))
            f = open(filepath, 'w')
            k = u.identities['evm'][old_chain_spec.fork()][sub_old_chain_str][0]
            k = to_checksum_address(strip_0x(k))
            try:
                tag_data = {'tags': user_tags.get(k)}
            except KeyError:
                logg.warning('missing tag for {}, adding defaults {}'.format(k, args.default_tag))
                for tag in args.default_tag:
                    tag_data['tags'].append(tag)
            for tag in args.tag:
                tag_data['tags'].append(tag)

            f.write(json.dumps(tag_data))
            f.close()

            os.symlink(os.path.realpath(filepath), custom_filepath)


            i += 1
            sys.stdout.write('imported {} {}'.format(i, u).ljust(200) + "\r")
        
            j += 1
            if j == batch_size:
                time.sleep(batch_delay)
                j = 0

    #fi.close()
