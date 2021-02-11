
#  Refactored bloxberg node

The original bloxberg node config was kind of annoying so I am running it more like vanilla parity. This way you can pass command flags directly to parity.
## Make some keys
```
docker build -t bloxie . && docker run -v ${PWD}/keys:/root/keys --rm -it -t bloxie account new --chain /root/bloxberg.json --keys-path /root/keys --password /root/validator.pwd
```

## Enter the signer address and passwords in the config files

validator.toml
```
[mining]
#CHANGE ENGINE SIGNER TO VALIDATOR ADDRESS
engine_signer = "0x0a7cac94bcd82ced7cd67651246dcb6a47553d53" <---- address goes here
reseal_on_txs = "none"
force_sealing = true
min_gas_price = 1000000
gas_floor_target = "10000000"
```

validator.pwd <--- put your password in here or leave it blank if you didn't enter a password.

## Run it!

Mount the keys folder on your host if you want to preserve the keys between runs...
```
docker run -v ${PWD}/keys:/root/keys  -it -t bloxie
```

---
# bloxbergValidatorSetup
This is a Docker image for running a validator node on the bloxberg blockchain. 

Remote Machine Minimum System Requirements:
* Ubuntu 16.04 or 18.04 Image (Other Operating Systems can work, but commands may have to be altered)
* Minimum 2 CPU
* Minimum 2GB RAM Memory
* We recommend for future proofing at least 100 GB of SSD storage.

These are simply the minimum requirements and we do recommend to allocate more resources to ensure stability.

With the latest update to parity 2.7, it is also necessary for your server CPU to support aes. This can be found by running:

```
cat /proc/cpuinfo
```
on the server and checking in the flags column for aes.

Additionally, the blockchain connects to other nodes via port 30303, so it is important this port is open via your firewall beforehand.

In the `docker-compose.yml` you will also see the ports 8545 (JSON-RPC API) and 8546 (Web-Socket). These can be used to interact with blockchain via means of your local node but don't need to be accesible over the internet.

## Setup Process

1. Clone the repository to the server you are hosting the validator node.
2. Edit the validator.yml with a text editor (nano or vim) and change the NATIP variable to your external IP. Save this file
3. Edit the `validator/validator.pwd` file and insert a secure password. This will be used to encrypt your private key.
4. Run 'sudo ./setup.sh'.
5. Run 'docker-compose -f validator.yml up'. This will start the docker container and generate an ethereum address and an enode address. Send these both to the bloxberg consortium.
6. Use Ctrl+C to shut down the docker container. Lastly, run 'docker-compose -f validator.yml up -d'. This will daemonize the container and start running the validator node in the background.
