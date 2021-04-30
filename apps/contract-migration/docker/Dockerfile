# syntax = docker/dockerfile:1.2
FROM python:3.8.6-slim-buster as compile-image

RUN apt-get update
RUN apt-get install -y --no-install-recommends git gcc g++ libpq-dev gawk jq telnet wget openssl iputils-ping gnupg socat bash procps make python2 cargo

RUN touch /etc/apt/sources.list.d/ethereum.list
RUN echo 'deb http://ppa.launchpad.net/ethereum/ethereum/ubuntu bionic main' > /etc/apt/sources.list.d/ethereum.list
RUN echo 'deb-src http://ppa.launchpad.net/ethereum/ethereum/ubuntu bionic main' >> /etc/apt/sources.list.d/ethereum.list

RUN cat etc/apt/sources.list.d/ethereum.list
RUN apt-key adv --keyserver keyserver.ubuntu.com  --recv-keys 2A518C819BE37D2C2031944D1C52189C923F6CA9

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

ARG pip_index_url=https://pypi.org/simple
ARG pip_extra_index_url=https://pip.grassrootseconomics.net:8433
ARG cic_base_version=0.1.2b6
ARG cic_eth_version=0.11.0b12
ARG sarafu_faucet_version=0.0.3a1
ARG sarafu_token_version=0.0.1a6
RUN pip install --user --index-url $pip_index_url --extra-index-url $pip_extra_index_url cic-base[full_graph]==$cic_base_version \
	cic-eth==$cic_eth_version \
	sarafu-faucet==$sarafu_faucet_version \
	sarafu-token==$sarafu_token_version

FROM python:3.8.6-slim-buster as runtime-image

RUN apt-get update
RUN apt-get install -y --no-install-recommends gnupg libpq-dev 
RUN apt-get install -y --no-install-recommends jq

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
