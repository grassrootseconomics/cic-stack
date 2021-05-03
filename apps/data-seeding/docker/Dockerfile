# syntax = docker/dockerfile:1.2
FROM python:3.8.6-slim-buster as compile-image

RUN apt-get update
RUN apt-get install -y --no-install-recommends git gcc g++ libpq-dev gawk jq telnet wget openssl iputils-ping gnupg socat bash procps make python2 cargo

WORKDIR /root
RUN mkdir -vp /usr/local/etc/cic

COPY data-seeding/requirements.txt . 

ARG EXTRA_INDEX_URL="https://pip.grassrootseconomics.net:8433"
RUN pip install --extra-index-url $EXTRA_INDEX_URL -r requirements.txt 

# -------------- begin runtime container ---------------- 
FROM python:3.8.6-slim-buster as runtime-image

RUN apt-get update
RUN apt-get install -y --no-install-recommends gnupg libpq-dev 
RUN apt-get install -y jq bash iputils-ping socat telnet dnsutils

COPY --from=compile-image /usr/local/bin/ /usr/local/bin/
COPY --from=compile-image /usr/local/etc/cic/ /usr/local/etc/cic/
COPY --from=compile-image /usr/local/lib/python3.8/site-packages/ \
                          /usr/local/lib/python3.8/site-packages/

WORKDIR root/

ENV EXTRA_INDEX_URL https://pip.grassrootseconomics.net:8433
# RUN useradd -u 1001 --create-home grassroots
# RUN adduser grassroots sudo && \
#     echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
# WORKDIR /home/grassroots

COPY data-seeding/ . 

# we copied these from the root build container.
# this is dumb though...I guess the compile image should have the same user
# RUN chown grassroots:grassroots -R /usr/local/lib/python3.8/site-packages/ 

# USER grassroots

ENTRYPOINT [ ]
