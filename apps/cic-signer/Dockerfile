ARG DOCKER_REGISTRY=registry.gitlab.com/grassrootseconomics

FROM $DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-e8eb2ee2 as dev

WORKDIR /root

RUN apt-get install libffi-dev -y

COPY requirements.txt . 

ARG EXTRA_PIP_INDEX_URL="https://pip.grassrootseconomics.net"
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL="https://pypi.org/simple"
#RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
RUN    pip install --index-url $PIP_INDEX_URL \
    --pre \
    --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

COPY . .

#RUN chmod +x *.sh
