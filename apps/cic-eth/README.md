# CIC-ETH

## Testing CIC-ETH locally.

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
