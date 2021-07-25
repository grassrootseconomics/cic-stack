# standard imports
import os

# external imports
import chainlib.cli 

# local imports
import cic_eth.cli

script_dir = os.path.dirname(os.path.realpath(__file__))
config_dir = os.path.join(script_dir, '..', '..', 'testdata', 'config')


def test_argumentparserto_config():

    argparser = cic_eth.cli.ArgumentParser()
    
    local_flags = 0xffff
    argparser.process_local_flags(local_flags) 
    argparser.add_argument('--foo', type=str)
    args = argparser.parse_args([
        '--redis-host', 'foo',
        '--redis-port', '123',
        '--redis-db', '0',
        '--redis-host-callback', 'bar',
        '--redis-port-callback', '456',
        '--redis-timeout', '10.0',
        '-q', 'baz',
        '--offset', '13',
        '--no-history',
        '-r','0xdeadbeef',
        '-vv',
        '--foo', 'bar',
        ])

    extra_args = {
            'foo': '_BARBARBAR',
            }
    config = cic_eth.cli.Config.from_args(args, chainlib.cli.argflag_std_base, local_flags, extra_args=extra_args, base_config_dir=config_dir)

    assert config.get('_BARBARBAR') == 'bar'
    assert config.get('REDIS_HOST') == 'foo'
    assert config.get('REDIS_PORT') == 123
    assert config.get('REDIS_DB') == 0
    assert config.get('_REDIS_HOST_CALLBACK') == 'bar'
    assert config.get('_REDIS_PORT_CALLBACK') == 456
    assert config.get('REDIS_TIMEOUT') == 10.0
    assert config.get('CELERY_QUEUE') == 'baz'
    assert config.get('SYNCER_NO_HISTORY') == True
    assert config.get('SYNCER_OFFSET') == 13
    assert config.get('CIC_REGISTRY_ADDRESS') == '0xdeadbeef'

