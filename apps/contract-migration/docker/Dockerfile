ARG DEV_DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DEV_DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-55da5f4e

WORKDIR /root

RUN touch /etc/apt/sources.list.d/ethereum.list
RUN echo 'deb http://ppa.launchpad.net/ethereum/ethereum/ubuntu bionic main' > /etc/apt/sources.list.d/ethereum.list
RUN echo 'deb-src http://ppa.launchpad.net/ethereum/ethereum/ubuntu bionic main' >> /etc/apt/sources.list.d/ethereum.list
RUN cat /etc/apt/sources.list.d/ethereum.list
RUN apt-key adv --keyserver keyserver.ubuntu.com  --recv-keys 2A518C819BE37D2C2031944D1C52189C923F6CA9

RUN mkdir -vp /usr/local/etc/cic

ENV CONFINI_DIR /usr/local/etc/cic/


COPY config_template/ /usr/local/etc/cic/
COPY requirements.txt . 

RUN apt-get install libffi-dev

ARG pip_index_url=https://pypi.org/simple
ARG EXTRA_PIP_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL="https://pypi.org/simple"
ARG pip_trusted_host=pypi.org
RUN pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt 

COPY override_requirements.txt . 

RUN pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r override_requirements.txt 

COPY . .
RUN chmod +x *.sh
