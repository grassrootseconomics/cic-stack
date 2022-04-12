## Instructions on how to bootstrap before setting up the services

### Prerequisites
* Install docker
* Install docker-compose

### Running the bootstrap
The bootstrap is run once to populate the services with necessary data

Run in the following order in the root of this repository. Each run must be complete before beginning the next run

```angular2html
RUN_MASK=1 RPC_PROVIDER=http://evm:8545 docker-compose up bootstrap 
RUN_MASK=2 RPC_PROVIDER=http://evm:8545 docker-compose up bootstrap 
RUN_MASK=4 RPC_PROVIDER=http://evm:8545 docker-compose up bootstrap 
RUN_MASK=8 RPC_PROVIDER=http://evm:8545 docker-compose up bootstrap 
RUN_MASK=16 RPC_PROVIDER=http://evm:8545 docker-compose up bootstrap 
RUN_MASK=32 RPC_PROVIDER=http://evm:8545 docker-compose up bootstrap 

```
### Running the services
Ensure you run this to stop and delete the containers and volumes before each run 
```angular2html
docker-compose down && docker volume prune --force

```
To run the services:
```
docker-compose up
```
