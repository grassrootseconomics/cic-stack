import { Injectable } from '@angular/core';
import { first } from 'rxjs/operators';
import { BehaviorSubject, Observable } from 'rxjs';
import { environment } from '@src/environments/environment';
import { Envelope, User } from 'cic-client-meta';
import { UserService } from '@app/_services/user.service';
import { Keccak } from 'sha3';
import { utils } from 'ethers';
import { add0x, fromHex, strip0x, toHex } from '@src/assets/js/ethtx/hex';
import { Tx } from '@src/assets/js/ethtx';
import { toValue } from '@src/assets/js/ethtx/tx';
import * as secp256k1 from 'secp256k1';
import { defaultAccount } from '@app/_models';
import { LoggingService } from '@app/_services/logging.service';
import { HttpClient } from '@angular/common/http';
import { CICRegistry } from '@cicnet/cic-client';
import { RegistryService } from '@app/_services/registry.service';
import Web3 from 'web3';
import { Web3Service } from '@app/_services/web3.service';
import { KeystoreService } from '@app/_services/keystore.service';
const vCard = require('vcard-parser');

@Injectable({
  providedIn: 'root',
})
export class TransactionService {
  transactions: any[] = [];
  private transactionList = new BehaviorSubject<any[]>(this.transactions);
  transactionsSubject = this.transactionList.asObservable();
  web3: Web3;
  registry: CICRegistry;

  constructor(
    private httpClient: HttpClient,
    private userService: UserService,
    private loggingService: LoggingService
  ) {
    this.web3 = Web3Service.getInstance();
  }

  async init(): Promise<void> {
    this.registry = await RegistryService.getRegistry();
  }

  getAllTransactions(offset: number, limit: number): Observable<any> {
    return this.httpClient.get(`${environment.cicCacheUrl}/tx/${offset}/${limit}`);
  }

  getAddressTransactions(address: string, offset: number, limit: number): Observable<any> {
    return this.httpClient.get(`${environment.cicCacheUrl}/tx/user/${address}/${offset}/${limit}`);
  }

  async setTransaction(transaction, cacheSize: number): Promise<void> {
    if (this.transactions.find((cachedTx) => cachedTx.tx.txHash === transaction.tx.txHash)) {
      return;
    }
    transaction.value = Number(transaction.value);
    transaction.type = 'transaction';
    try {
      if (transaction.from === environment.trustedDeclaratorAddress) {
        transaction.sender = defaultAccount;
        this.userService.addAccount(defaultAccount, cacheSize);
      } else {
        this.userService
          .getAccountDetailsFromMeta(await User.toKey(transaction.from))
          .pipe(first())
          .subscribe(
            (res) => {
              transaction.sender = this.getAccountInfo(res, cacheSize);
            },
            (error) => {
              this.loggingService.sendErrorLevelMessage(
                `Account with address ${transaction.from} not found`,
                this,
                { error }
              );
            }
          );
      }
      if (transaction.to === environment.trustedDeclaratorAddress) {
        transaction.recipient = defaultAccount;
        this.userService.addAccount(defaultAccount, cacheSize);
      } else {
        this.userService
          .getAccountDetailsFromMeta(await User.toKey(transaction.to))
          .pipe(first())
          .subscribe(
            (res) => {
              transaction.recipient = this.getAccountInfo(res, cacheSize);
            },
            (error) => {
              this.loggingService.sendErrorLevelMessage(
                `Account with address ${transaction.to} not found`,
                this,
                { error }
              );
            }
          );
      }
    } finally {
      this.addTransaction(transaction, cacheSize);
    }
  }

  async setConversion(conversion, cacheSize): Promise<void> {
    if (this.transactions.find((cachedTx) => cachedTx.tx.txHash === conversion.tx.txHash)) {
      return;
    }
    conversion.type = 'conversion';
    conversion.fromValue = Number(conversion.fromValue);
    conversion.toValue = Number(conversion.toValue);
    try {
      if (conversion.trader === environment.trustedDeclaratorAddress) {
        conversion.sender = conversion.recipient = defaultAccount;
        this.userService.addAccount(defaultAccount, cacheSize);
      } else {
        this.userService
          .getAccountDetailsFromMeta(await User.toKey(conversion.trader))
          .pipe(first())
          .subscribe(
            (res) => {
              conversion.sender = conversion.recipient = this.getAccountInfo(res);
            },
            (error) => {
              this.loggingService.sendErrorLevelMessage(
                `Account with address ${conversion.trader} not found`,
                this,
                { error }
              );
            }
          );
      }
    } finally {
      this.addTransaction(conversion, cacheSize);
    }
  }

  addTransaction(transaction, cacheSize: number): void {
    const savedIndex = this.transactions.findIndex((tx) => tx.tx.txHash === transaction.tx.txHash);
    if (savedIndex === 0) {
      return;
    }
    if (savedIndex > 0) {
      this.transactions.splice(savedIndex, 1);
    }
    this.transactions.unshift(transaction);
    if (this.transactions.length > cacheSize) {
      this.transactions.length = Math.min(this.transactions.length, cacheSize);
    }
    this.transactionList.next(this.transactions);
  }

  resetTransactionsList(): void {
    this.transactions = [];
    this.transactionList.next(this.transactions);
  }

  getAccountInfo(account: string, cacheSize: number = 100): any {
    const accountInfo = Envelope.fromJSON(JSON.stringify(account)).unwrap().m.data;
    accountInfo.vcard = vCard.parse(atob(accountInfo.vcard));
    this.userService.addAccount(accountInfo, cacheSize);
    return accountInfo;
  }

  async transferRequest(
    tokenAddress: string,
    senderAddress: string,
    recipientAddress: string,
    value: number
  ): Promise<any> {
    const transferAuthAddress = await this.registry.getContractAddressByName(
      'TransferAuthorization'
    );
    const hashFunction = new Keccak(256);
    hashFunction.update('createRequest(address,address,address,uint256)');
    const hash = hashFunction.digest();
    const methodSignature = hash.toString('hex').substring(0, 8);
    const abiCoder = new utils.AbiCoder();
    const abi = abiCoder.encode(
      ['address', 'address', 'address', 'uint256'],
      [senderAddress, recipientAddress, tokenAddress, value]
    );
    const data = fromHex(methodSignature + strip0x(abi));
    const tx = new Tx(environment.bloxbergChainId);
    tx.nonce = await this.web3.eth.getTransactionCount(senderAddress);
    tx.gasPrice = Number(await this.web3.eth.getGasPrice());
    tx.gasLimit = 8000000;
    tx.to = fromHex(strip0x(transferAuthAddress));
    tx.value = toValue(value);
    tx.data = data;
    const txMsg = tx.message();
    const keystore = await KeystoreService.getKeystore();
    const privateKey = keystore.getPrivateKey();
    if (!privateKey.isDecrypted()) {
      const password = window.prompt('password');
      await privateKey.decrypt(password);
    }
    const signatureObject = secp256k1.ecdsaSign(txMsg, privateKey.keyPacket.privateParams.d);
    const r = signatureObject.signature.slice(0, 32);
    const s = signatureObject.signature.slice(32);
    const v = signatureObject.recid;
    tx.setSignature(r, s, v);
    const txWire = add0x(toHex(tx.serializeRLP()));
    const result = await this.web3.eth.sendSignedTransaction(txWire);
    this.loggingService.sendInfoLevelMessage(`Result: ${result}`);
    const transaction = await this.web3.eth.getTransaction(result.transactionHash);
    this.loggingService.sendInfoLevelMessage(`Transaction: ${transaction}`);
  }
}
