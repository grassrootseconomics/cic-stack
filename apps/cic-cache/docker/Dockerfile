# syntax = docker/dockerfile:1.2
FROM registry.gitlab.com/grassrootseconomics/cic-base-images:python-3.8.6-dev-55da5f4e as dev
 
# RUN pip install $pip_extra_index_url_flag cic-base[full_graph]==0.1.2b9

COPY requirements.txt .
#RUN pip install $pip_extra_index_url_flag -r test_requirements.txt
#RUN pip install $pip_extra_index_url_flag .
#RUN pip install .[server]

ARG EXTRA_INDEX_URL="https://pip.grassrootseconomics.net:8433"
ARG GITLAB_PYTHON_REGISTRY="https://gitlab.com/api/v4/projects/27624814/packages/pypi/simple"
ARG EXTRA_PIP_ARGS=""
RUN --mount=type=cache,mode=0755,target=/root/.cache/pip \
    pip install --index-url https://pypi.org/simple  \
	  --extra-index-url $GITLAB_PYTHON_REGISTRY --extra-index-url $EXTRA_INDEX_URL $EXTRA_PIP_ARGS \
    -r requirements.txt

COPY . . 

RUN python setup.py install

# ini files in config directory defines the configurable parameters for the application
# they can all be overridden by environment variables
# to generate a list of environment variables from configuration, use: confini-dump -z <dir> (executable provided by confini package)
COPY config/ .

# for db migrations
RUN git clone https://github.com/vishnubob/wait-for-it.git /usr/local/bin/wait-for-it/
COPY cic_cache/db/migrations/ /usr/local/share/cic-cache/alembic/

COPY /docker/start_tracker.sh ./start_tracker.sh
COPY /docker/db.sh ./db.sh
RUN chmod 755 ./*.sh
# Tracker
# ENTRYPOINT ["/usr/local/bin/cic-cache-tracker", "-vv"]
# Server
# ENTRYPOINT [ "/usr/local/bin/uwsgi", "--wsgi-file", "/usr/local/lib/python3.8/site-packages/cic_cache/runnable/server.py", "--http", ":80", "--pyargv", "-vv" ]
ENTRYPOINT []
