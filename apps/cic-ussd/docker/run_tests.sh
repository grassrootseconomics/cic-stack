#! /bin/bash

set -e


pip install --extra-index-url https://pip.grassrootseconomics.net \
--extra-index-url https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple \
-r test_requirements.txt 

export PYTHONPATH=. && pytest -x --cov=cic_ussd --cov-fail-under=90 --cov-report term-missing tests/cic_ussd
