FROM python:3.7

ENV VIRTUAL_ENV=/venv

RUN python3 -m venv $VIRTUAL_ENV

ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY ./ ./

RUN pip install --extra-index-url https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple --extra-index-url https://pip.grassrootseconomics.net -r requirements.txt -r test_requirements.txt

CMD PYTHONPATH=. python -m pytest -rf run tests/