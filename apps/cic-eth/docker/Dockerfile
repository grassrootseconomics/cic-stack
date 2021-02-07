FROM python:3.8.6-slim-buster

RUN apt-get update && \
	apt install -y gcc gnupg libpq-dev wget make g++ gnupg bash procps

WORKDIR /usr/src/cic-eth

ARG pip_extra_index_url_flag='--index https://pypi.org/simple --extra-index-url https://pip.grassrootseconomics.net:8433'
ARG root_requirement_file='requirements.txt'
# Copy shared requirements from top of mono-repo
RUN echo "copying root req file ${root_requirement_file}"
COPY $root_requirement_file .
RUN pip install -r $root_requirement_file $pip_extra_index_url_flag

COPY cic-eth/scripts/ scripts/
COPY cic-eth/setup.cfg cic-eth/setup.py ./
COPY cic-eth/cic_eth/ cic_eth/
# Copy app specific requirements
COPY cic-eth/requirements.txt .
COPY cic-eth/test_requirements.txt .
RUN	pip install $pip_extra_index_url_flag .

COPY cic-eth/docker/* ./ 
RUN chmod 755 *.sh
COPY cic-eth/tests/ tests/

# # ini files in config directory defines the configurable parameters for the application
# # they can all be overridden by environment variables
# # to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
COPY cic-eth/config/ /usr/local/etc/cic-eth/
COPY cic-eth/cic_eth/db/migrations/ /usr/local/share/cic-eth/alembic/
COPY cic-eth/crypto_dev_signer_config/ /usr/local/etc/crypto-dev-signer/
