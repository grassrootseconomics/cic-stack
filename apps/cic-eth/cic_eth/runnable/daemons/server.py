# standard imports
import logging
import multiprocessing
import os
import sys

# local imports
import cic_eth.cli
import gunicorn.app.base
from cic_eth.server.app import create_app
from cic_eth.server.getters import RedisGetter

# Parse args
arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_server
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
args, unknown = argparser.parse_known_args(args=sys.argv[1:])

# Setup Config
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags)

# Setup Logging
log_level = 'warning'
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)
gunicorn_logger = logging.getLogger('gunicorn.error')
logger.handlers = gunicorn_logger.handlers
logger.setLevel(gunicorn_logger.level)

if args.vv:
    log_level = 'debug'
    logger.setLevel(logging.DEBUG)

elif args.v:
    log_level = 'info'
    logger.setLevel(logging.INFO)


# Setup Celery App
celery_app = cic_eth.cli.CeleryApp.from_config(config)
celery_app.set_default()

# Required Config
chain_spec = config.get('CHAIN_SPEC')
celery_queue = config.get('CELERY_QUEUE')
redis_host = config.get('REDIS_HOST')
redis_port = config.get('REDIS_PORT')
redis_db = config.get('REDIS_DB')
redis_timeout = config.get('REDIS_TIMEOUT')
server_port = config.get('SERVER_PORT', 5000)
server_host = config.get('SERVER_HOST', "0.0.0.0")
server_workers = config.get('SERVER_WORKERS', 1)
server_config = config.get('SERVER_CONFIG', None)

# Create FastAPI App
app = create_app(chain_spec, redis_host, redis_port, redis_db,
                 redis_timeout, RedisGetter, celery_queue=celery_queue)


class StandaloneApplication(gunicorn.app.base.Application):

    def __init__(self, app, options=None, config_path=None):
        self.options = options or {}
        self.application = app
        super().__init__()

    def load_config(self):
        if self.options.get('config'):
            self.load_config_from_file(self.options.get('config'))
        else:
            config = {key: value for key, value in self.options.items()
                      if key in self.cfg.settings and value is not None}
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

    def load(self):
        return self.application


def main():
    options = {
        'bind': f'{server_host}:{server_port}',
        'workers': server_workers,
        'worker_class': 'uvicorn.workers.UvicornWorker',
        'loglevel': log_level,
    }
    # If Server Config  Override all Options
    if server_config is not None:
        config_exists = os.path.exists(path=server_config)

        if config_exists:
            logger.info(msg=f"Loading config from {server_config}")
            options = {
                'config': server_config,
            }
        else:
            logger.warning(msg=f"Config file {server_config} does not exist")
    
    StandaloneApplication(app, options).run()


if __name__ == "__main__":
    main()
