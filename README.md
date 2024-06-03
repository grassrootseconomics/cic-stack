# cic-deploy
 
## Usage

1. Create a `ge` overlay network with `docker network create ge`
2. Bring up the inidividual services and their dependant containers with `docker-compose up -d`.
3. Optionally, bring up the `caddy` container if you want to expose the API to the internet.
4. Optionally, bring up the `observability` containers if you have an [Uptrace](https://uptrace.dev) deployment/account.


## License

[AGPL-3.0](LICENSE).