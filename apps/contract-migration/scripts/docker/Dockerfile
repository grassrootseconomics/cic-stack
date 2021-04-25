FROM python:3.8.5-slim-buster

RUN apt-get update
RUN apt-get install -y --no-install-recommends git gcc g++ libpq-dev gawk jq telnet wget openssl iputils-ping gnupg socat bash procps make python2 cargo
RUN pip install pip
RUN pip install --extra-index-url https://pip.grassrootseconomics.net:8433 -r requirements.txt
