import { Injectable } from '@angular/core';
import { MutableKeyStore, MutablePgpKeyStore } from '@app/_pgp';

@Injectable({
  providedIn: 'root',
})
export class KeystoreService {
  private static mutableKeyStore: MutableKeyStore;

  constructor() {}

  public static async getKeystore(): Promise<MutableKeyStore> {
    return new Promise(async (resolve, reject) => {
      if (!KeystoreService.mutableKeyStore) {
        this.mutableKeyStore = new MutablePgpKeyStore();
        await this.mutableKeyStore.loadKeyring();
        return resolve(KeystoreService.mutableKeyStore);
      }
      return resolve(KeystoreService.mutableKeyStore);
    });
  }
}
