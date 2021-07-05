FROM python:3.8.6-slim-buster as compile

WORKDIR /usr/src/cic-eth

RUN apt-get update && \
	apt install -y gcc gnupg libpq-dev wget make g++ gnupg bash procps git

#RUN python -m venv venv && . venv/bin/activate

ARG pip_extra_index_url_flag='--index https://pypi.org/simple --extra-index-url https://pip.grassrootseconomics.net:8433'
ARG EXTRA_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG GITLAB_PYTHON_REGISTRY="https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple"
RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip install semver

COPY cic-eth/ .
RUN	pip install --extra-index-url $GITLAB_PYTHON_REGISTRY \
    	--extra-index-url $EXTRA_INDEX_URL .

# --- TEST IMAGE ---
FROM python:3.8.6-slim-buster as test 

RUN apt-get update && \
	apt install -y gcc gnupg libpq-dev wget make g++ gnupg bash procps git

WORKDIR /usr/src/cic-eth

RUN /usr/local/bin/python -m pip install --upgrade pip

COPY --from=compile /usr/local/bin/ /usr/local/bin/
COPY --from=compile /usr/local/lib/python3.8/site-packages/ \
                          /usr/local/lib/python3.8/site-packages/
# TODO we could use venv inside container to isolate the system and app deps further
# COPY --from=compile /usr/src/cic-eth/ .
# RUN . venv/bin/activate

ARG ="https://pip.grassrootseconomics.net:8433"
ARG GITLAB_PYTHON_REGISTRY="https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple"

COPY cic-eth/test_requirements.txt .
RUN	pip install --extra-index-url $GITLAB_PYTHON_REGISTRY \
    	--extra-index-url $EXTRA_INDEX_URL .

COPY cic-eth . 

ENV PYTHONPATH .

ENTRYPOINT ["pytest"]

# --- RUNTIME ---
FROM python:3.8.6-slim-buster as runtime 

RUN apt-get update && \
	apt install -y gnupg libpq-dev procps

WORKDIR /usr/src/cic-eth

COPY --from=compile /usr/local/bin/ /usr/local/bin/
COPY --from=compile /usr/local/lib/python3.8/site-packages/ \
                          /usr/local/lib/python3.8/site-packages/

COPY cic-eth/docker/* ./ 
RUN chmod 755 *.sh

COPY cic-eth/scripts/ scripts/
# # ini files in config directory defines the configurable parameters for the application
# # they can all be overridden by environment variables
# # to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
COPY cic-eth/config/ /usr/local/etc/cic-eth/
COPY cic-eth/cic_eth/db/migrations/ /usr/local/share/cic-eth/alembic/
COPY cic-eth/crypto_dev_signer_config/ /usr/local/etc/crypto-dev-signer/

COPY util/liveness/health.sh /usr/local/bin/health.sh

