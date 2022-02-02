ARG DOCKER_REGISTRY="registry.gitlab.com/grassrootseconomics"

FROM $DOCKER_REGISTRY/parity:v2.5.13-stable

# root user for installing os dep's and setting file permissions 
# RUN apt-get update && sudo apt-get -y install sed
USER root
WORKDIR /root

# ARG BASE_PATH=root/.local/share/io.parity.ethereum/
ARG KEY_PATH=/root/keys/
# mount a key volume locally if you want to persist keys between runs
# to generate new account + keys run:
#
RUN mkdir -p $KEY_PATH
COPY ./validator/bloxberg.json \
     ./validator/bootnodes.txt \
     ./validator/validator.pwd \
     ./validator/validator.toml \
     /root/

COPY keys/ /root/keys/

# RUN chown -R parity:parity $HOME/ && \
#     chmod -R 775 $HOME/ && \
#     chmod g+s $HOME/
# USER parity

ENTRYPOINT [ "parity" ]
CMD [ "--config", "/root/validator.toml", "--keys-path", "/root/keys/", "--password", "/root/validator.pwd" ]
