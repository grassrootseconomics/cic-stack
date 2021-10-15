ARG DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-55da5f4e as dev


WORKDIR /root

COPY requirements.txt . 

ARG pip_index_url=https://pypi.org/simple
ARG EXTRA_PIP_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL="https://pypi.org/simple"
ARG pip_trusted_host=pypi.org
RUN    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --force-reinstall \
    --no-cache \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

COPY . .

#RUN chmod +x *.sh
