ARG DEV_DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DEV_DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-55da5f4e

# Copy just the requirements and install....this _might_ give docker a hint on caching but we 
# do load these all into setup.py later
# TODO can we take all the requirements out of setup.py and just do a pip install -r requirements.txt && python setup.py
#COPY cic-eth/requirements.txt .

ARG EXTRA_PIP_INDEX_URL=https://pip.grassrootseconomics.net:8433
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL=https://pypi.org/simple

RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
        cic-eth-aux-erc20-demurrage-token~=0.0.2a7


COPY *requirements.txt ./
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt \
    -r services_requirements.txt \
    -r admin_requirements.txt 
  
COPY . .
RUN python setup.py install

ENV PYTHONPATH .


COPY docker/entrypoints/* ./ 
RUN chmod 755 *.sh

# # ini files in config directory defines the configurable parameters for the application
# # they can all be overridden by environment variables
# # to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
#COPY config/ /usr/local/etc/cic-eth/
COPY cic_eth/db/migrations/ /usr/local/share/cic-eth/alembic/
COPY crypto_dev_signer_config/ /usr/local/etc/crypto-dev-signer/

# TODO this kind of code sharing across projects should be discouraged...can we make util a library?
#COPY util/liveness/health.sh /usr/local/bin/health.sh
ENTRYPOINT []

## ------------------ PRODUCTION CONTAINER ----------------------
#FROM python:3.8.6-slim-buster as prod 
#
#RUN apt-get update && \
#	apt install -y gnupg libpq-dev procps
#
#WORKDIR /root
#
#COPY --from=dev /usr/local/bin/ /usr/local/bin/
#COPY --from=dev /usr/local/lib/python3.8/site-packages/ \
#                          /usr/local/lib/python3.8/site-packages/
#
#COPY docker/entrypoints/* ./ 
#RUN chmod 755 *.sh
#
## # ini files in config directory defines the configurable parameters for the application
## # they can all be overridden by environment variables
## # to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
#COPY config/ /usr/local/etc/cic-eth/
#COPY cic_eth/db/migrations/ /usr/local/share/cic-eth/alembic/
#COPY crypto_dev_signer_config/ /usr/local/etc/crypto-dev-signer/
#COPY scripts/ scripts/ 
#
## TODO this kind of code sharing across projects should be discouraged...can we make util a library?
##COPY util/liveness/health.sh /usr/local/bin/health.sh
#
#ENTRYPOINT []

