FROM python:3.8.6-slim-buster

RUN apt-get update && \
	apt-get install -y git gcc g++ libpq-dev && \
	apt-get install -y vim gawk jq telnet openssl iputils-ping curl wget gnupg socat bash procps make python2 postgresql-client cargo

WORKDIR /usr/src/cic-base
COPY . /usr/src/cic-base/

#RUN mkdir python 
#WORKDIR ./python
#COPY ./pep503.sh .
#RUN pip download --no-cache-dir --extra-index-url https://pip.grassrootseconomics.net:8433 cic-base[full_graph]==0.1.1a6
RUN pip install -r requirements.txt
RUN python setup.py bdist_wheel
RUN pip download --extra-index-url https://pip.grassrootseconomics.net:8433 dist/$(basename $(ls dist/*))
RUN mkdir packages && \
	cd packages && \
	bash ../docker/pep503.sh ..

WORKDIR /usr/src/cic-base/packages

RUN ls
RUN ls ..

ENTRYPOINT ["python", "-m", "http.server", "8080"]
