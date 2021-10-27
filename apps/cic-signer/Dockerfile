ARG DEV_DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DEV_DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-55da5f4e as dev

WORKDIR /root

RUN apt-get install libffi-dev -y

COPY requirements.txt . 

ARG EXTRA_PIP_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL="https://pypi.org/simple"
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

COPY . .

#RUN chmod +x *.sh
