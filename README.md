# CIC Stack (cic-internal-integration)

Documentation as well as community contribution guides can be found [here](https://docs.grassecon.org) and the source of those docs can be found [here](https://gitlab.com/grassrootseconomics/grassrootseconomics.gitlab.io) 

## Getting started 

This repo uses docker-compose and docker buildkit. Set the following environment variables to get started:


```
export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1
```

start services, database, redis and local ethereum node
```
docker-compose up -d
```

Run app/contract-migration to deploy contracts
```
RUN_MASK=3 docker-compose up contract-migration
```

stop cluster
```
docker-compose down
```

stop cluster and delete data
```
docker-compose down -v --remove-orphans
```

rebuild an images
```
docker-compose up --build <service_name>
```

to delete the buildkit cache
```
docker builder prune --filter type=exec.cachemount
```
