# cic-internal-integration

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


