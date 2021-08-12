// Third party imports
import Web3 from 'web3';

// Application imports
import { Web3Service } from '@app/_services/web3.service';
import { environment } from '@src/environments/environment';

/** Fetch the account registry contract's ABI. */
const abi: Array<any> = require('@src/assets/js/block-sync/data/AccountsIndex.json');
/** Establish a connection to the blockchain network. */
const web3: Web3 = Web3Service.getInstance();

/**
 * Provides an instance of the accounts registry contract.
 * Allows querying of accounts that have been registered as valid accounts in the network.
 *
 * @remarks
 * This is our interface to the accounts registry contract.
 */
export class AccountIndex {
  /** The instance of the account registry contract. */
  contract: any;
  /** The deployed account registry contract's address. */
  contractAddress: string;
  /** The account address of the account that deployed the account registry contract. */
  signerAddress: string;

  /**
   * Create a connection to the deployed account registry contract.
   *
   * @param contractAddress - The deployed account registry contract's address.
   * @param signerAddress - The account address of the account that deployed the account registry contract.
   */
  constructor(contractAddress: string, signerAddress?: string) {
    this.contractAddress = contractAddress;
    this.contract = new web3.eth.Contract(abi, this.contractAddress);
    // TODO this signer logic should be part of the web3service
    // if signer address is not passed (for example in user service) then
    // this fallsback to a web3 wallet that is not even connected???
    if (signerAddress) {
      this.signerAddress = signerAddress;
    } else {
      this.signerAddress = web3.eth.accounts[0];
    }
  }

  /**
   * Registers an account to the accounts registry.
   * Requires availability of the signer address.
   *
   * @async
   * @example
   * Prints "true" for registration of '0xc0ffee254729296a45a3885639AC7E10F9d54979':
   * ```typescript
   * console.log(await addToAccountRegistry('0xc0ffee254729296a45a3885639AC7E10F9d54979'));
   * ```
   *
   * @param address - The account address to be registered to the accounts registry contract.
   * @returns true - If registration is successful or account had already been registered.
   */
  public async addToAccountRegistry(address: string): Promise<boolean> {
    if (!(await this.haveAccount(address))) {
      return await this.contract.methods.add(address).send({ from: this.signerAddress });
    }
    return true;
  }

  /**
   * Checks whether a specific account address has been registered in the accounts registry.
   * Returns "true" for available and "false" otherwise.
   *
   * @async
   * @example
   * Prints "true" or "false" depending on whether '0xc0ffee254729296a45a3885639AC7E10F9d54979' has been registered:
   * ```typescript
   * console.log(await haveAccount('0xc0ffee254729296a45a3885639AC7E10F9d54979'));
   * ```
   *
   * @param address - The account address to be validated.
   * @returns true - If the address has been registered in the accounts registry.
   */
  public async haveAccount(address: string): Promise<boolean> {
    return (await this.contract.methods.have(address).call()) !== 0;
  }

  /**
   * Returns a specified number of the most recently registered accounts.
   *
   * @async
   * @example
   * Prints an array of accounts:
   * ```typescript
   * console.log(await last(5));
   * ```
   *
   * @param numberOfAccounts - The number of accounts to return from the accounts registry.
   * @returns An array of registered account addresses.
   */
  public async last(numberOfAccounts: number): Promise<Array<string>> {
    const count: number = await this.totalAccounts();
    let lowest: number = count - numberOfAccounts;
    if (lowest < 0) {
      lowest = 0;
    }
    const accounts: Array<string> = [];
    for (let i = count - 1; i >= lowest; i--) {
      const account: string = await this.contract.methods.entry(i).call();
      accounts.push(account);
    }
    return accounts;
  }

  /**
   * Returns the total number of accounts that have been registered in the network.
   *
   * @async
   * @example
   * Prints the total number of registered accounts:
   * ```typescript
   * console.log(await totalAccounts());
   * ```
   *
   * @returns The total number of registered accounts.
   */
  public async totalAccounts(): Promise<number> {
    return await this.contract.methods.entryCount().call();
  }
}
