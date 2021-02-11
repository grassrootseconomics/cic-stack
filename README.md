# cic-internal-integration

## Getting started 

## Make some keys

```
docker build -t bloxie . && docker run -v "$(pwd)/keys:/root/keys" --rm -it -t bloxie account new --chain /root/bloxberg.json --keys-path /root/keys
```


### Prepare the repo

This is stuff we need to put in  makefile but for now...

File mounts and permisssions need to be set
```
chmod -R 755 scripts/initdb apps/cic-meta/scripts/initdb
````

start cluster
```
docker-compose up
```

stop cluster
```
docker-compose down
```

delete data
```
docker-compose down -v
```

rebuild an images
```
docker-compose up --build <service_name>
```

Deployment variables are writtend to service-configs/.env after everthing is up.

