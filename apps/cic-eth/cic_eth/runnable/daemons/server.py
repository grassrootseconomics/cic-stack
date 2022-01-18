# standard imports
import logging

# local imports
import cic_eth.cli
from cic_eth.server.app import create_app
from cic_eth.server.getters import RedisGetter

# Parse args
arg_flags = cic_eth.cli.argflag_std_base
local_arg_flags = cic_eth.cli.argflag_local_taskcallback
argparser = cic_eth.cli.ArgumentParser(arg_flags)
argparser.process_local_flags(local_arg_flags)
args = argparser.parse_args()

# Setup Config
config = cic_eth.cli.Config.from_args(args, arg_flags, local_arg_flags)

# Define log levels
if args.vv:
    logging.getLogger().setLevel(logging.DEBUG)
elif args.v:
    logging.getLogger().setLevel(logging.INFO)


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

# Create App
app = create_app(chain_spec, redis_host, redis_port, redis_db, redis_timeout, RedisGetter, celery_queue=celery_queue)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
