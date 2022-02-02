# standard imports
import hashlib
import json
import logging
import os
from typing import Union

# external imports
import cic_eth.cli
from chainlib.chain import ChainSpec
from chainlib.eth.connection import EthHTTPConnection
from chainlib.eth.gas import OverrideGasOracle
from chainlib.eth.nonce import RPCNonceOracle
from cic_types.condiments import MetadataPointer
from cic_types.ext.metadata import MetadataRequestsHandler, Signer
from eth_address_declarator import Declarator
from eth_address_declarator.declarator import AddressDeclarator
from funga.eth.signer import EIP155Signer
from funga.eth.keystore.dict import DictKeystore
from hexathon import add_0x, strip_0x
from okota.token_index.index import to_identifier

# local imports

logging.basicConfig(level=logging.WARNING)
logg = logging.getLogger()

script_dir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.join(script_dir, '..')
base_config_dir = os.path.join(root_dir, 'config', 'proofs')
token_data_dir = os.path.join(root_dir, 'token_data')

arg_flags = cic_eth.cli.argflag_std_base
arg_parser = cic_eth.cli.ArgumentParser(arg_flags)
arg_parser.add_argument('--token-symbol', type=str, help='Token symbol whose metadata is being processed.')
arg_parser.add_argument('--address-declarator', type=str, help='Address to address declarator contract')
arg_parser.add_argument('--signer-address', type=str, help='Wallet keyfile address')
arg_parser.add_argument('--write-metadata', dest='write_metadata', action='store_true', help='Write metadata to data aviilability layer')
arg_parser.add_argument('--write-chain', dest='write_chain', action='store_true', help='Write metadata proofs to chain')
arg_parser.add_argument('-e', type=str, help='Token address.')
args = arg_parser.parse_args()
config = cic_eth.cli.Config.from_args(args, arg_flags, 0, base_config_dir=base_config_dir)

token_metadata = os.path.join(token_data_dir, 'meta.json')
token_proof = os.path.join(token_data_dir, 'proof.json')


def hash_proof(data: bytes) -> hex:
    hash_object = hashlib.sha256()
    hash_object.update(data)
    return hash_object.digest().hex()


def init_meta():
    MetadataRequestsHandler.base_url = config.get('META_URL')
    Signer.gpg_path = config.get('PGP_EXPORT_DIR')
    Signer.key_file_path = f"{config.get('PGP_KEYS_PATH')}{config.get('PGP_PRIVATE_KEYS')}"
    Signer.gpg_passphrase = config.get('PGP_PASSPHRASE')


def wrapper(chain_spec: ChainSpec, rpc: EthHTTPConnection) -> Declarator:
    gas_oracle = OverrideGasOracle(limit=AddressDeclarator.gas(), conn=rpc)
    nonce_oracle = RPCNonceOracle(address=add_0x(args.signer_address.lower()), conn=rpc)
    keystore = DictKeystore()
    keystore.import_keystore_file(keystore_file=config.get('WALLET_KEY_FILE'))
    signer = EIP155Signer(keystore)
    return Declarator(chain_spec, gas_oracle=gas_oracle, nonce_oracle=nonce_oracle, signer=signer)


def write_to_declarator(contract_address: hex, contract_wrapper: Declarator, proof: any, rpc: EthHTTPConnection,
                        signer_address: hex, token_address: hex):
    operation = contract_wrapper.add_declaration(contract_address, signer_address, token_address, proof)
    results = rpc.do(operation[1])
    rpc.wait(results)


def write_metadata(writer: MetadataRequestsHandler, data: Union[dict, str]):
    writer.create(data)


if __name__ == '__main__':
    init_meta()
    chain_spec = ChainSpec.from_chain_str(config.get('CHAIN_SPEC'))

    token_address_bytes = bytes.fromhex(strip_0x(args.e))
    token_symbol_bytes = args.token_symbol.encode('utf-8')
    token_meta_file = open(token_metadata, 'r')
    token_proof_file = open(token_proof, 'r')
    token_meta_data = json.load(token_meta_file)
    token_proof_data = json.load(token_proof_file)
    token_meta_file.close()
    token_proof_file.close()

    hashed_token_proof = hash_proof(data=json.dumps(token_proof_data).encode('utf-8'))

    if args.write_chain:
        rpc = EthHTTPConnection(url=config.get('RPC_PROVIDER'), chain_spec=chain_spec)
        contract_wrapper = wrapper(chain_spec, rpc)

        logg.debug(f'Writing hashed proof: {hashed_token_proof}')
        write_to_declarator(contract_address=args.address_declarator,
                            contract_wrapper=contract_wrapper,
                            proof=hashed_token_proof,
                            rpc=rpc,
                            signer_address=args.signer_address,
                            token_address=args.e)

        hashed_token_proof_rev = to_identifier(args.token_symbol)
        logg.debug(f'Writing hashed proof: {hashed_token_proof}')
        write_to_declarator(contract_address=args.address_declarator,
                            contract_wrapper=contract_wrapper,
                            proof=hashed_token_proof_rev,
                            rpc=rpc,
                            signer_address=args.signer_address,
                            token_address=args.e)

    if args.write_metadata:
        token_meta_writer = MetadataRequestsHandler(cic_type=MetadataPointer.TOKEN_META, identifier=token_address_bytes)
        write_metadata(token_meta_writer, token_meta_data)

        token_meta_symbol_writer = MetadataRequestsHandler(cic_type=MetadataPointer.TOKEN_META_SYMBOL,
                                                           identifier=token_symbol_bytes)
        write_metadata(token_meta_symbol_writer, token_meta_data)

        token_proof_writer = MetadataRequestsHandler(cic_type=MetadataPointer.TOKEN_PROOF, identifier=token_address_bytes)
        write_metadata(token_proof_writer, token_proof_data)

        token_proof_symbol_writer = MetadataRequestsHandler(cic_type=MetadataPointer.TOKEN_PROOF_SYMBOL,
                                                            identifier=token_symbol_bytes)
        write_metadata(token_proof_symbol_writer, token_proof_data)

        identifier = bytes.fromhex(hashed_token_proof)
        token_immutable_proof_writer = MetadataRequestsHandler(cic_type=MetadataPointer.NONE, identifier=identifier)
        write_metadata(token_immutable_proof_writer, token_proof_data)
