# syntax = docker/dockerfile:1.2
FROM registry.gitlab.com/grassrootseconomics/cic-base-images:python-3.8.6-dev-55da5f4e

WORKDIR /root

RUN touch /etc/apt/sources.list.d/ethereum.list
RUN echo 'deb http://ppa.launchpad.net/ethereum/ethereum/ubuntu bionic main' > /etc/apt/sources.list.d/ethereum.list
RUN echo 'deb-src http://ppa.launchpad.net/ethereum/ethereum/ubuntu bionic main' >> /etc/apt/sources.list.d/ethereum.list
RUN cat /etc/apt/sources.list.d/ethereum.list
RUN apt-key adv --keyserver keyserver.ubuntu.com  --recv-keys 2A518C819BE37D2C2031944D1C52189C923F6CA9

#RUN apt-get install solc

RUN mkdir -vp /usr/local/etc/cic

ENV CONFINI_DIR /usr/local/etc/cic/


COPY config_template/ /usr/local/etc/cic/
COPY requirements.txt . 
COPY override_requirements.txt . 

ARG pip_index_url=https://pypi.org/simple
ARG EXTRA_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG EXTRA_PIP_ARGS=""
ARG GITLAB_PYTHON_REGISTRY="https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple"
ARG pip_trusted_host=pypi.org
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url https://pypi.org/simple \
    --pre \
    --force-reinstall \
    --trusted-host $pip_trusted_host \
    --extra-index-url $GITLAB_PYTHON_REGISTRY --extra-index-url $EXTRA_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt 

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url https://pypi.org/simple \
    --force-reinstall \
    --pre \
    --trusted-host $pip_trusted_host \
    --extra-index-url $GITLAB_PYTHON_REGISTRY --extra-index-url $EXTRA_INDEX_URL $EXTRA_PIP_ARGS \
    -r override_requirements.txt 


COPY . .
RUN chmod +x *.sh
