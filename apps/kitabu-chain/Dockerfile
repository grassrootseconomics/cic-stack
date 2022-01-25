ARG DOCKER_REGISTRY=docker.io

FROM $DOCKER_REGISTRY/debian:buster-slim

WORKDIR /root

RUN apt-get update -y 
RUN apt-get install -y cmake llvm git python3-venv curl clang

RUN git clone --depth 1 --branch v3.3.3 https://git.grassecon.net/grassrootseconomics/openethereum

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- --default-toolchain 1.47.0 --profile minimal -y

WORKDIR /root/openethereum
RUN export PATH=/root/.cargo/bin:$PATH && \
	cargo -v build --release --features final	

WORKDIR /root

ARG EXTRA_PIP_INDEX_URL="https://pip.grassrootseconomics.net"
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL="https://pypi.org/simple"

RUN apt-get install -y python3-pip
RUN apt-get install -y libssl-dev autoconf libtool pkg-config
RUN pip3 install --index-url $PIP_INDEX_URL \
	--pre \
	--extra-index-url $EXTRA_PIP_INDEX_URL \
	funga-eth==0.5.4b2

ENV VANITY_STRING=${VANITY_STRING:-"Kitabu Sarafu Karibu Sana"}

RUN apt-get install -y bsdmainutils
COPY ./extra.sh ./extra.sh
COPY ./aux/bash-templater/templater.sh ./templater.sh
COPY ./kitabu*template ./

ENV WALLET_PASSPHRASE=test
ARG DEV_ETH_ACCOUNT_CONTRACT_DEPLOYER=0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C
ARG DEV_ETH_GENESIS_START_GAS=0x204fce5e3e25026110000000

RUN bash extra.sh

RUN export DEV_ETH_ACCOUNT_VALIDATOR="0x$(eth-keyfile -d keyfile_validator.json)" && \
	export DEV_ETH_GENESIS_EXTRA_DATA="0x$(cat .extra)" && \
	bash templater.sh kitabu.json.template > kitabu.json

RUN mkdir -vp .openethereum/data/keys/kitabu_sarafu && \
	cp -v keyfile_validator.json .openethereum/data/keys/kitabu_sarafu/

RUN export CONFIG_DIR=/root && \
	export DATA_DIR=/root/.openethereum && \
	export SIGNER_ADDRESS="0x$(eth-keyfile -d keyfile_validator.json)" && \
	export LOG_DIR=/root && \
	bash templater.sh kitabu.toml.template > kitabu.toml

RUN echo -n test > kitabu.pwd

# ENTRYPOINT [ '/bin/sh', '-c', 'openethereum/target/release/openethereum', '-c', '/root/kitabu.toml' ]
