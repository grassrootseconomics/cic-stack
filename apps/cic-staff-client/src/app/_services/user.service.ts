import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { environment } from '@src/environments/environment';
import { first } from 'rxjs/operators';
import { ArgPair, Envelope, Phone, Syncable, User } from 'cic-client-meta';
import { AccountDetails } from '@app/_models';
import { LoggingService } from '@app/_services/logging.service';
import { TokenService } from '@app/_services/token.service';
import { MutableKeyStore, PGPSigner, Signer } from '@app/_pgp';
import { RegistryService } from '@app/_services/registry.service';
import { CICRegistry } from '@cicnet/cic-client';
import { personValidation, updateSyncable, vcardValidation } from '@app/_helpers';
import { add0x, strip0x } from '@src/assets/js/ethtx/hex';
import { KeystoreService } from '@app/_services/keystore.service';
import * as Automerge from 'automerge';
const vCard = require('vcard-parser');

@Injectable({
  providedIn: 'root',
})
export class UserService {
  headers: HttpHeaders = new HttpHeaders({ 'x-cic-automerge': 'client' });
  keystore: MutableKeyStore;
  signer: Signer;
  registry: CICRegistry;

  accounts: Array<AccountDetails> = [];
  private accountsList: BehaviorSubject<Array<AccountDetails>> = new BehaviorSubject<
    Array<AccountDetails>
  >(this.accounts);
  accountsSubject: Observable<Array<AccountDetails>> = this.accountsList.asObservable();

  actions: Array<any> = [];
  private actionsList: BehaviorSubject<any> = new BehaviorSubject<any>(this.actions);
  actionsSubject: Observable<Array<any>> = this.actionsList.asObservable();

  categories: object = {};
  private categoriesList: BehaviorSubject<object> = new BehaviorSubject<object>(this.categories);
  categoriesSubject: Observable<object> = this.categoriesList.asObservable();

  history: Array<any> = [];
  private historyList: BehaviorSubject<any> = new BehaviorSubject<any>(this.history);
  historySubject: Observable<Array<any>> = this.historyList.asObservable();

  constructor(
    private httpClient: HttpClient,
    private loggingService: LoggingService,
    private tokenService: TokenService
  ) {}

  async init(): Promise<void> {
    this.keystore = await KeystoreService.getKeystore();
    this.signer = new PGPSigner(this.keystore);
    this.registry = await RegistryService.getRegistry();
  }

  resetPin(phone: string): Observable<any> {
    const params: HttpParams = new HttpParams().set('phoneNumber', phone);
    return this.httpClient.put(`${environment.cicUssdUrl}/pin`, { params });
  }

  getAccountStatus(phone: string): Observable<any> {
    const params: HttpParams = new HttpParams().set('phoneNumber', phone);
    return this.httpClient.get(`${environment.cicUssdUrl}/pin`, { params });
  }

  getLockedAccounts(offset: number, limit: number): Observable<any> {
    return this.httpClient.get(`${environment.cicUssdUrl}/accounts/locked/${offset}/${limit}`);
  }

  async changeAccountInfo(
    address: string,
    name: string,
    phoneNumber: string,
    age: string,
    type: string,
    bio: string,
    gender: string,
    businessCategory: string,
    userLocation: string,
    location: string,
    locationType: string,
    oldPhoneNumber: string
  ): Promise<any> {
    const accountInfo = await this.loadChangesToAccountStructure(
      name,
      phoneNumber,
      age,
      type,
      bio,
      gender,
      businessCategory,
      userLocation,
      location,
      locationType
    );
    const accountKey: string = await User.toKey(address);
    this.getAccountDetailsFromMeta(accountKey)
      .pipe(first())
      .subscribe(
        async (res) => {
          const syncableAccount: Syncable = Envelope.fromJSON(JSON.stringify(res)).unwrap();
          const update: Array<ArgPair> = [];
          for (const prop of Object.keys(accountInfo)) {
            update.push(new ArgPair(prop, accountInfo[prop]));
          }
          updateSyncable(update, 'client-branch', syncableAccount);
          await personValidation(syncableAccount.m.data);
          await this.updateMeta(syncableAccount, accountKey, this.headers);
        },
        async (error) => {
          this.loggingService.sendErrorLevelMessage(
            'Cannot find account info in meta service',
            this,
            { error }
          );
          const syncableAccount: Syncable = new Syncable(accountKey, accountInfo);
          await this.updateMeta(syncableAccount, accountKey, this.headers);
        }
      );
    if (phoneNumber !== oldPhoneNumber) {
      const oldPhoneKey: string = await Phone.toKey(oldPhoneNumber);
      const newPhoneKey: string = await Phone.toKey(phoneNumber);
      const newPhoneData: Syncable = new Syncable(newPhoneKey, strip0x(address));
      await this.updateMeta(newPhoneData, newPhoneKey, this.headers);
      const oldPhoneData: Syncable = new Syncable(oldPhoneKey, '');
      await this.updateMeta(oldPhoneData, oldPhoneKey, this.headers);
    }
    return accountKey;
  }

  async updateMeta(
    syncableAccount: Syncable,
    accountKey: string,
    headers: HttpHeaders
  ): Promise<any> {
    const envelope: Envelope = await this.wrap(syncableAccount, this.signer);
    const reqBody: string = envelope.toJSON();
    this.httpClient
      .put(`${environment.cicMetaUrl}/${accountKey}`, reqBody, { headers })
      .pipe(first())
      .subscribe((res) => {
        this.loggingService.sendInfoLevelMessage(`Response: ${res}`);
      });
  }

  getActions(): void {
    this.httpClient
      .get(`${environment.cicCacheUrl}/actions`)
      .pipe(first())
      .subscribe((res) => this.actionsList.next(res));
  }

  getActionById(id: string): Observable<any> {
    return this.httpClient.get(`${environment.cicCacheUrl}/actions/${id}`);
  }

  approveAction(id: string): Observable<any> {
    return this.httpClient.post(`${environment.cicCacheUrl}/actions/${id}`, { approval: true });
  }

  revokeAction(id: string): Observable<any> {
    return this.httpClient.post(`${environment.cicCacheUrl}/actions/${id}`, { approval: false });
  }

  getAccountDetailsFromMeta(userKey: string): Observable<any> {
    return this.httpClient.get(`${environment.cicMetaUrl}/${userKey}`, { headers: this.headers });
  }

  wrap(syncable: Syncable, signer: Signer): Promise<Envelope> {
    return new Promise<Envelope>(async (resolve, reject) => {
      syncable.setSigner(signer);
      syncable.onwrap = async (env) => {
        if (env === undefined) {
          reject();
          return;
        }
        resolve(env);
      };
      await syncable.sign();
    });
  }

  async loadAccounts(limit: number = 100, offset: number = 0): Promise<void> {
    try {
      const accountRegistry = await RegistryService.getAccountRegistry();
      const accountAddresses: Array<string> = await accountRegistry.last(offset + limit);
      this.loggingService.sendInfoLevelMessage(accountAddresses);
      if (typeof Worker !== 'undefined') {
        const worker = new Worker('@app/_workers/fetch-accounts.worker', { type: 'module' });
        worker.onmessage = ({ data }) => {
          if (data) {
            this.tokenService.load.subscribe(async (status: boolean) => {
              if (status) {
                data.balance = await this.tokenService.getTokenBalance(
                  data.identities.evm[`bloxberg:${environment.bloxbergChainId}`][0]
                );
              }
            });
            this.addAccount(data, limit);
          }
        };
        worker.postMessage({
          addresses: accountAddresses.slice(offset, offset + limit),
          url: environment.cicMetaUrl,
          token: sessionStorage.getItem(btoa('CICADA_SESSION_TOKEN')),
        });
      } else {
        this.loggingService.sendInfoLevelMessage(
          'Web workers are not supported in this environment'
        );
        for (const accountAddress of accountAddresses.slice(offset, offset + limit)) {
          await this.getAccountByAddress(accountAddress, limit);
        }
      }
    } catch (error) {
      this.loggingService.sendErrorLevelMessage('Unable to load accounts.', 'user.service', error);
      throw error;
    }
  }

  async getAccountByAddress(
    accountAddress: string,
    limit: number = 100,
    history: boolean = false
  ): Promise<Observable<AccountDetails>> {
    const accountSubject: Subject<any> = new Subject<any>();
    this.getAccountDetailsFromMeta(await User.toKey(add0x(accountAddress)))
      .pipe(first())
      .subscribe(async (res) => {
        const account: Syncable = Envelope.fromJSON(JSON.stringify(res)).unwrap();
        if (history) {
          try {
            // @ts-ignore
            this.historyList.next(Automerge.getHistory(account.m).reverse());
          } catch (error) {
            this.loggingService.sendErrorLevelMessage('No history found', this, { error });
          }
        }
        const accountInfo = account.m.data;
        await personValidation(accountInfo);
        this.tokenService.load.subscribe(async (status: boolean) => {
          if (status) {
            accountInfo.balance = await this.tokenService.getTokenBalance(
              accountInfo.identities.evm[`bloxberg:${environment.bloxbergChainId}`][0]
            );
          }
        });
        accountInfo.vcard = vCard.parse(atob(accountInfo.vcard));
        await vcardValidation(accountInfo.vcard);
        this.addAccount(accountInfo, limit);
        accountSubject.next(accountInfo);
      });
    return accountSubject.asObservable();
  }

  async getAccountByPhone(
    phoneNumber: string,
    limit: number = 100
  ): Promise<Observable<AccountDetails>> {
    const accountSubject: Subject<any> = new Subject<any>();
    this.getAccountDetailsFromMeta(await Phone.toKey(phoneNumber))
      .pipe(first())
      .subscribe(async (res) => {
        const response: Syncable = Envelope.fromJSON(JSON.stringify(res)).unwrap();
        const address: string = response.m.data;
        const account: Observable<AccountDetails> = await this.getAccountByAddress(address, limit);
        account.subscribe((result) => {
          accountSubject.next(result);
        });
      });
    return accountSubject.asObservable();
  }

  resetAccountsList(): void {
    this.accounts = [];
    this.accountsList.next(this.accounts);
  }

  getCategories(): void {
    this.httpClient
      .get(`${environment.cicMetaUrl}/categories`)
      .pipe(first())
      .subscribe((res: object) => this.categoriesList.next(res));
  }

  getCategoryByProduct(product: string, categories: object): string {
    const keywords = product.toLowerCase().split(' ');
    for (const keyword of keywords) {
      const queriedCategory: string = Object.keys(categories).find((key) =>
        categories[key].includes(keyword)
      );
      if (queriedCategory) {
        return queriedCategory;
      }
    }
    return 'other';
  }

  getAccountTypes(): Observable<any> {
    return this.httpClient.get(`${environment.cicMetaUrl}/accounttypes`);
  }

  getTransactionTypes(): Observable<any> {
    return this.httpClient.get(`${environment.cicMetaUrl}/transactiontypes`);
  }

  getGenders(): Observable<any> {
    return this.httpClient.get(`${environment.cicMetaUrl}/genders`);
  }

  addAccount(account: AccountDetails, cacheSize: number): void {
    const savedIndex = this.accounts.findIndex(
      (acc) =>
        acc.identities.evm[`bloxberg:${environment.bloxbergChainId}`][0] ===
        account.identities.evm[`bloxberg:${environment.bloxbergChainId}`][0]
    );
    if (savedIndex === 0) {
      return;
    }
    if (savedIndex > 0) {
      this.accounts.splice(savedIndex, 1);
    }
    this.accounts.unshift(account);
    if (this.accounts.length > cacheSize) {
      this.accounts.length = Math.min(this.accounts.length, cacheSize);
    }
    this.accountsList.next(this.accounts);
  }

  async loadChangesToAccountStructure(
    name: string,
    phoneNumber: string,
    age: string,
    type: string,
    bio: string,
    gender: string,
    businessCategory: string,
    userLocation: string,
    location: string,
    locationType: string
  ): Promise<AccountDetails> {
    const accountInfo: any = {
      vcard: {
        fn: [{}],
        n: [{}],
        tel: [{}],
      },
      location: {},
    };
    if (name) {
      accountInfo.vcard.fn[0].value = name;
      accountInfo.vcard.n[0].value = name.split(' ');
    }
    if (phoneNumber) {
      accountInfo.vcard.tel[0].value = phoneNumber;
    }
    if (bio) {
      accountInfo.products = [bio];
    }
    if (gender) {
      accountInfo.gender = gender;
    }
    if (age) {
      accountInfo.age = age;
    }
    if (type) {
      accountInfo.type = type;
    }
    if (businessCategory) {
      accountInfo.category = businessCategory;
    }
    if (location) {
      accountInfo.location.area = location;
    }
    if (userLocation) {
      accountInfo.location.area_name = userLocation;
    }
    if (locationType) {
      accountInfo.location.area_type = locationType;
    }
    await vcardValidation(accountInfo.vcard);
    accountInfo.vcard = btoa(vCard.generate(accountInfo.vcard));
    return accountInfo;
  }
}
