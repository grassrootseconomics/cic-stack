# syntax = docker/dockerfile:1.2
FROM python:3.8.6-slim-buster as compile-image

RUN apt-get update
RUN apt-get install -y --no-install-recommends git gcc g++ libpq-dev gawk jq telnet wget openssl iputils-ping gnupg socat bash procps make python2 cargo

RUN apt-get install -y software-properties-common
RUN add-apt-repository ppa:ethereum/ethereum
RUN apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 1C52189C923F6CA9
RUN apt-get update
RUN apt-get install solc
RUN pip install --upgrade pip

WORKDIR /root
RUN mkdir -vp /usr/local/etc/cic

COPY contract-migration/nvm.sh .
ENV CONFINI_DIR /usr/local/etc/cic/
RUN mkdir -vp $CONFINI_DIR

ARG cic_config_commit=35c69ba75f00c8147150acf325565d5391cf25bf
ARG cic_config_url=https://gitlab.com/grassrootseconomics/cic-config.git/
RUN echo Install confini schema files && \
	git clone --depth 1 $cic_config_url cic-config && \
	cd cic-config && \
	git fetch --depth 1 origin $cic_config_commit && \
	git checkout $cic_config_commit && \	
	cp -v *.ini $CONFINI_DIR

ARG cic_contracts_commit=698ef3a30fde8d7f2c498f1208fb0ff45d665501
ARG cic_contracts_url=https://gitlab.com/grassrootseconomics/cic-contracts.git/
RUN echo Install ABI collection for solidity interfaces used across all components && \
	git clone --depth 1 $cic_contracts_url cic-contracts && \
	cd cic-contracts && \
	git fetch --depth 1 origin $cic_contracts_commit && \
	git checkout $cic_contracts_commit && \
	make install

# Install nvm with node and npm
# https://stackoverflow.com/questions/25899912/how-to-install-nvm-in-docker
ENV NVM_DIR /root/.nvm
ENV NODE_VERSION 15.3.0
ENV BANCOR_NODE_VERSION 10.16.0

RUN wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.37.2/install.sh | bash \
	&& . $NVM_DIR/nvm.sh \
	&& nvm install $NODE_VERSION \
	&& nvm alias default $NODE_VERSION \
	&& nvm use $NODE_VERSION
# && chown -R root:root "$NVM_DIR/versions/node/v$NODE_VERSION"

ENV NODE_PATH $NVM_DIR/versions/node//v$NODE_VERSION/lib/node_modules
ENV PATH      $NVM_DIR/versions/node//v$NODE_VERSION/bin:$PATH

RUN useradd --create-home grassroots
WORKDIR /home/grassroots
USER grassroots

ARG pip_extra_index_url=https://pip.grassrootseconomics.net:8433
ARG cic_base_version=0.1.2a28
ARG cic_eth_version=0.10.1a5+build.5cc1526c
ARG sarafu_faucet_version=0.0.2a9
ARG cic_contracts_version=0.0.2a2
RUN pip install --user --extra-index-url $pip_extra_index_url cic-base[full_graph]==$cic_base_version \
	cic-eth==$cic_eth_version \
	cic-contracts==$cic_contracts_version \
	sarafu-faucet==$sarafu_faucet_version

FROM python:3.8.6-slim-buster as runtime-image

RUN apt-get update
RUN apt-get install -y --no-install-recommends gnupg libpq-dev

COPY --from=compile-image /usr/local/bin/ /usr/local/bin/
COPY --from=compile-image /usr/local/etc/cic/ /usr/local/etc/cic/

RUN useradd --create-home grassroots
WORKDIR /home/grassroots
# COPY python dependencies to user dir
COPY --from=compile-image /home/grassroots/.local .local
ENV PATH=/home/grassroots/.local/bin:$PATH

COPY contract-migration/testdata/pgp testdata/pgp
COPY contract-migration/sarafu_declaration.json sarafu_declaration.json
COPY contract-migration/keystore keystore
COPY contract-migration/envlist .

# RUN chown grassroots:grassroots .local/

RUN mkdir -p /tmp/cic/config
RUN chown grassroots:grassroots /tmp/cic/config
# A shared output dir for environment configs
RUN chmod a+rwx /tmp/cic/config 

COPY contract-migration/*.sh ./
RUN chown grassroots:grassroots -R .
RUN chmod gu+x *.sh


USER grassroots

ENTRYPOINT [ ]
