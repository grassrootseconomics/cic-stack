ARG DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DOCKER_REGISTRY/cic-base-images:python-3.8.6-dev-e8eb2ee2

WORKDIR /root

RUN mkdir -vp /usr/local/etc/cic

ARG NPM_REPOSITORY=${NPM_REPOSITORY:-https://registry.npmjs.org}
RUN npm config set snyk=false
#RUN npm config set registry={NPM_REPOSITORY}
RUN npm config set registry=${NPM_REPOSITORY}

# copy the dependencies
COPY package.json package-lock.json ./
RUN --mount=type=cache,mode=0755,target=/root/.npm \
    npm set cache /root/.npm && \
    npm cache verify && \
    npm ci --verbose


#RUN npm ci --production --verbose
#RUN --mount=type=cache,mode=0755,target=/root/node_modules npm install

#COPY common/ cic_ussd/common/
COPY requirements.txt .
COPY config/ config

ARG EXTRA_PIP_INDEX_URL=https://pip.grassrootseconomics.net
ARG EXTRA_PIP_ARGS=""
ARG PIP_INDEX_URL=https://pypi.org/simple

RUN  pip install --index-url $PIP_INDEX_URL  \
     --pre \
     --extra-index-url $EXTRA_PIP_INDEX_URL $EXTRA_PIP_ARGS \
     -r requirements.txt

COPY . .

ENTRYPOINT [ ]
