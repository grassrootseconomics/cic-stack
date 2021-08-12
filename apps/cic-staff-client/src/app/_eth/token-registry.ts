// Third party imports
import Web3 from 'web3';

// Application imports
import { environment } from '@src/environments/environment';
import { Web3Service } from '@app/_services/web3.service';

/** Fetch the token registry contract's ABI. */
const abi: Array<any> = require('@src/assets/js/block-sync/data/TokenUniqueSymbolIndex.json');
/** Establish a connection to the blockchain network. */
const web3: Web3 = Web3Service.getInstance();

/**
 * Provides an instance of the token registry contract.
 * Allows querying of tokens that have been registered as valid tokens in the network.
 *
 * @remarks
 * This is our interface to the token registry contract.
 */
export class TokenRegistry {
  /** The instance of the token registry contract. */
  contract: any;
  /** The deployed token registry contract's address. */
  contractAddress: string;
  /** The account address of the account that deployed the token registry contract. */
  signerAddress: string;

  /**
   * Create a connection to the deployed token registry contract.
   *
   * @param contractAddress - The deployed token registry contract's address.
   * @param signerAddress - The account address of the account that deployed the token registry contract.
   */
  constructor(contractAddress: string, signerAddress?: string) {
    this.contractAddress = contractAddress;
    this.contract = new web3.eth.Contract(abi, this.contractAddress);
    if (signerAddress) {
      this.signerAddress = signerAddress;
    } else {
      this.signerAddress = web3.eth.accounts[0];
    }
  }

  /**
   * Returns the address of the token with a given identifier.
   *
   * @async
   * @example
   * Prints the address of the token with the identifier 'sarafu':
   * ```typescript
   * console.log(await addressOf('sarafu'));
   * ```
   *
   * @param identifier - The name or identifier of the token to be fetched from the token registry.
   * @returns The address of the token assigned the specified identifier in the token registry.
   */
  public async addressOf(identifier: string): Promise<string> {
    const id: string = web3.eth.abi.encodeParameter('bytes32', web3.utils.toHex(identifier));
    return await this.contract.methods.addressOf(id).call();
  }

  /**
   * Returns the address of a token with the given serial in the token registry.
   *
   * @async
   * @example
   * Prints the address of the token with the serial '2':
   * ```typescript
   * console.log(await entry(2));
   * ```
   *
   * @param serial - The serial number of the token to be fetched.
   * @return The address of the token with the specified serial number.
   */
  public async entry(serial: number): Promise<string> {
    return await this.contract.methods.entry(serial).call();
  }

  /**
   * Returns the total number of tokens that have been registered in the network.
   *
   * @async
   * @example
   * Prints the total number of registered tokens:
   * ```typescript
   * console.log(await totalTokens());
   * ```
   *
   * @returns The total number of registered tokens.
   */
  public async totalTokens(): Promise<number> {
    return await this.contract.methods.entryCount().call();
  }
}
