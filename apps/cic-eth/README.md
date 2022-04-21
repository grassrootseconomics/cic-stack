# CIC-ETH

## Services

### Eth Server (cic-eth-server)

Uses Gunicorn + UnicornWorkers + FastAPI

### Configuration and Running

#### Docker-Compose

```bash
docker-compose up --build cic-eth-server
```
Once this is up and running head over to http://0.0.0.0:5000/docs 
#### CLI Usage
Ensure dependencies and services are installed/running

**With a Config file**

_Note: The config file will override all other server args_
```bash
cic-eth-serverd --server-config ./docker/gunicorn.conf.py
```
**Basic**
```
cic-eth-serverd -v
cic-eth-serverd --help
cic-eth-serverd --host 0.0.0.0 --port 8080 --workers 4
```
<details>
  <summary>All</summary>
  
  
```
usage: cic-eth-serverd [-h] [-v] [-vv] [-c CONFIG] [-n NAMESPACE] [--dumpconfig {env,ini}] [--env-prefix ENV_PREFIX] [--raw] [--redis-host REDIS_HOST]
                       [--redis-port REDIS_PORT] [--redis-db REDIS_DB] [--redis-host-callback REDIS_HOST_CALLBACK] [--redis-port-callback REDIS_PORT_CALLBACK]
                       [--redis-timeout REDIS_TIMEOUT] [--celery-scheme CELERY_SCHEME] [--celery-host CELERY_HOST] [--celery-port CELERY_PORT]
                       [--celery-db CELERY_DB] [--celery-result-scheme CELERY_RESULT_SCHEME] [--celery-result-host CELERY_RESULT_HOST]
                       [--celery-result-port CELERY_RESULT_PORT] [--celery-result-db CELERY_RESULT_DB] [--celery-no-result] [-q CELERY_QUEUE]
                       [--server-port SERVER_PORT] [--server-host SERVER_HOST] [--server-workers SERVER_WORKERS] [--server-config SERVER_CONFIG]

optional arguments:
-h, --help show this help message and exit
-v Be verbose
-vv Be more verbose
-c CONFIG, --config CONFIG
Configuration directory
-n NAMESPACE, --namespace NAMESPACE
Configuration namespace
--dumpconfig {env,ini}
Output configuration and quit. Use with --raw to omit values and output schema only.
--env-prefix ENV_PREFIX
environment prefix for variables to overwrite configuration
--raw Do not decode output
--redis-host REDIS_HOST
redis host to use for task submission
--redis-port REDIS_PORT
redis host to use for task submission
--redis-db REDIS_DB redis db to use
--redis-host-callback REDIS_HOST_CALLBACK
redis host to use for callback (defaults to redis host)
--redis-port-callback REDIS_PORT_CALLBACK
redis port to use for callback (defaults to redis port)
--redis-timeout REDIS_TIMEOUT
Redis callback timeout
--celery-scheme CELERY_SCHEME
Celery broker scheme (defaults to "redis")
--celery-host CELERY_HOST
Celery broker host (defaults to redis host)
--celery-port CELERY_PORT
Celery broker port (defaults to redis port)
--celery-db CELERY_DB
Celery broker db (defaults to redis db)
--celery-result-scheme CELERY_RESULT_SCHEME
Celery result backend scheme (defaults to celery broker scheme)
--celery-result-host CELERY_RESULT_HOST
Celery result backend host (defaults to celery broker host)
--celery-result-port CELERY_RESULT_PORT
Celery result backend port (defaults to celery broker port)
--celery-result-db CELERY_RESULT_DB
Celery result backend db (defaults to celery broker db)
--celery-no-result Disable the Celery results backend
-q CELERY_QUEUE, --celery-queue CELERY_QUEUE
Task queue
--server-port SERVER_PORT
Server port
--server-host SERVER_HOST
Server host
--server-workers SERVER_WORKERS
The number of worker processes for handling requests
--server-config SERVER_CONFIG
Gunicorn config file, or python module. It will override all other server args. (see
https://docs.gunicorn.org/en/19.2.1/settings.html#config-file)

```
</details>
<br/>

## Testing.

### Setup a Virtual Env

```bash
python3 -m venv ./venv # Python 3.9
source ./venv/activate
```

### Running All Unit Tests

```bash
bash ./tests/run_tests.sh # This will also install required dependencies
```

### Running Specific Unit Tests

Ensure that:

- You have called `bash ./tests/run_tests.sh` at least once or run the following to install required dependencies
- You have activated the virtual environment

```
pip install --extra-index-url https://pip.grassrootseconomics.net --extra-index-url https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple \
-r admin_requirements.txt \
-r services_requirements.txt \
-r test_requirements.txt
```

Then here is an example that only runs tests with the keyword(-k) `test_server`

```bash
pytest -s -v --log-cli-level DEBUG --log-level DEBUG -k test_server
```
