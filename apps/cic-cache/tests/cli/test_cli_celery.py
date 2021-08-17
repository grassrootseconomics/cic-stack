# standard imports
import tempfile

# local imports
import cic_cache.cli


def test_cli_celery():
    cf = tempfile.mkdtemp()

    config = {
            'CELERY_RESULT_URL': 'filesystem://' + cf,
            }
    cic_cache.cli.CeleryApp.from_config(config)

    config['CELERY_BROKER_URL'] = 'filesystem://' + cf
    cic_cache.cli.CeleryApp.from_config(config)
