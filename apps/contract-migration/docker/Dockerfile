#FROM ethereum/solc:0.6.12
FROM ethereum/solc:0.8.0

# The solc image messes up the alpine environment, so we have to go all over again
FROM alpine
COPY --from=0 /usr/bin/solc /usr/bin/solc

RUN apk update && \
	apk add make git
	
WORKDIR /usr/src

ARG cic_config_commit=35c69ba75f00c8147150acf325565d5391cf25bf
ARG cic_config_url=https://gitlab.com/grassrootseconomics/cic-config.git/
RUN echo Install confini schema files && \
	git clone --depth 1 $cic_config_url cic-config && \
	cd cic-config && \
	git fetch --depth 1 origin $cic_config_commit && \
	git checkout $cic_config_commit && \
	mkdir -vp /usr/local/etc/cic && \
	cp -v *.ini /usr/local/etc/cic/
ENV CONFINI_DIR /usr/local/etc/cic


ARG cic_contracts_commit=698ef3a30fde8d7f2c498f1208fb0ff45d665501
ARG cic_contracts_url=https://gitlab.com/grassrootseconomics/cic-contracts.git/
RUN echo Install ABI collection for solidity interfaces used across all components && \
	git clone --depth 1 $cic_contracts_url cic-contracts && \
	cd cic-contracts && \
	git fetch --depth 1 origin $cic_contracts_commit && \
	git checkout $cic_contracts_commit && \
	make install

#COPY ./Makefile ./cic-contracts/Makefile
#COPY ./*.sol ./cic-contracts/

#RUN cd cic-contracts && \
#	make -B && make install -B 

FROM python:3.8.6-slim-buster

COPY --from=1 /usr/local/share/cic/ /usr/local/share/cic/
COPY --from=1 /usr/local/etc/ /usr/local/etc/

LABEL authors="Louis Holbrook <dev@holbrook.no> 0826EDA1702D1E87C6E2875121D2E7BB88C2A746"
LABEL spdx-license-identifier="GPL-3.0-or-later"
LABEL description="Base layer for buiding development images for the cic component suite"

RUN apt-get update && \
	apt-get install -y git gcc g++ libpq-dev && \
	apt-get install -y vim gawk jq telnet openssl iputils-ping curl wget gnupg socat bash procps make python2 postgresql-client


RUN echo installing nodejs tooling

COPY contract-migration/nvm.sh /root/

# Install nvm with node and npm
# https://stackoverflow.com/questions/25899912/how-to-install-nvm-in-docker
ENV NVM_DIR /root/.nvm
ENV NODE_VERSION 15.3.0
ENV BANCOR_NODE_VERSION 10.16.0

RUN wget -qO- https://raw.githubusercontent.com/nvm-sh/nvm/v0.37.2/install.sh | bash \
	&& . $NVM_DIR/nvm.sh \
	&& nvm install $NODE_VERSION \
	&& nvm alias default $NODE_VERSION \
	&& nvm use $NODE_VERSION \
# So many ridiculously stupid issues with node in docker that take oceans of absolutely wasted time to resolve
# owner of these files is "1001" by default - wtf
	&& chown -R root:root "$NVM_DIR/versions/node/v$NODE_VERSION"

ENV NODE_PATH $NVM_DIR/versions/node//v$NODE_VERSION/lib/node_modules
ENV PATH      $NVM_DIR/versions/node//v$NODE_VERSION/bin:$PATH


ARG pip_extra_index_url=https://pip.grassrootseconomics.net:8433

# This is a temporary solution for building the Bancor contracts using the bancor protocol repository truffle setup
# We should instead flatten the files ourselves and build them with solc in the first image layer in this file
ARG cic_bancor_commit=a04c7ae6882ea515938d852cc861d59a35070094
ARG cic_bancor_url=https://gitlab.com/grassrootseconomics/cic-bancor.git/
ARG cic_bancor_contracts_url=https://github.com/bancorprotocol/contracts-solidity
RUN echo Compile and install bancor protocol contracts && \
	git clone --depth 1 $cic_bancor_url cic-bancor && \
	cd cic-bancor && \
	git fetch --depth 1 origin $cic_bancor_commit && \
	git checkout $cic_bancor_commit && \
	# Apparently the git version here doesn't have set-url as a command. *sigh*
	#if [ ! -z $cic_bancor_contracts_url ]; then
	#	git submodule set-url bancor $cic_bancor_contracts_url
	#fi
	git submodule init && \
	git submodule update
RUN cd root && \
	. $NVM_DIR/nvm.sh &&\
	nvm install $BANCOR_NODE_VERSION && \
	nvm use $BANCOR_NODE_VERSION && \
	cd - && \
	cd cic-bancor/bancor && \
	npm install --python=/usr/bin/python2 && \
	node_modules/truffle/build/cli.bundled.js compile && \
	mkdir -vp /usr/local/share/cic/bancor/solidity/build  && \
	cp -vR solidity/build/contracts /usr/local/share/cic/bancor/solidity/build/
RUN cd cic-bancor/python && \
	pip install --extra-index-url $pip_extra_index_url .


RUN apt-get install -y cargo
ARG cic_base_version=0.1.1a23
RUN pip install  --extra-index-url $pip_extra_index_url cic-base[full_graph]==$cic_base_version

ARG cic_registry_version=0.5.3a24
RUN pip install  --extra-index-url $pip_extra_index_url  cic-registry==$cic_registry_version

WORKDIR /root

COPY contract-migration/testdata/pgp testdata/pgp
COPY contract-migration/wait-for-it.sh .
RUN chmod +x ./wait-for-it.sh

# COPY contract-migration/.env_config_template .env_config_template
# COPY contract-migration/.env_dockercompose_template .env_dockercompose_template

COPY contract-migration/reset.sh reset.sh
COPY contract-migration/from_env.sh from_env.sh
COPY contract-migration/seed_cic_eth.sh seed_cic_eth.sh
COPY contract-migration/sarafu_declaration.json sarafu_declaration.json
COPY contract-migration/keystore keystore

ENTRYPOINT [ "/bin/bash" ]
