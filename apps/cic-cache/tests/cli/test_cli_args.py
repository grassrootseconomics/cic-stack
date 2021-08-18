# standard imports
import os

# external imports
import chainlib.cli 

# local imports
import cic_cache.cli

script_dir = os.path.dirname(os.path.realpath(__file__))
config_dir = os.path.join(script_dir, '..', 'testdata', 'config')


def test_argumentparserto_config():

    argparser = cic_cache.cli.ArgumentParser()
    
    local_flags = 0xffff
    argparser.process_local_flags(local_flags) 
    argparser.add_argument('--foo', type=str)
    args = argparser.parse_args([
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
    config = cic_cache.cli.Config.from_args(args, chainlib.cli.argflag_std_base, local_flags, extra_args=extra_args, base_config_dir=config_dir)

    assert config.get('_BARBARBAR') == 'bar'
    assert config.get('CELERY_QUEUE') == 'baz'
    assert config.get('SYNCER_NO_HISTORY') == True
    assert config.get('SYNCER_OFFSET') == 13
    assert config.get('CIC_REGISTRY_ADDRESS') == '0xdeadbeef'

