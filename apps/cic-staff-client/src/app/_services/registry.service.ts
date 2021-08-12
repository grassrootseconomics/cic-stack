import { Injectable } from '@angular/core';
import { environment } from '@src/environments/environment';
import { CICRegistry, FileGetter } from '@cicnet/cic-client';
import { TokenRegistry, AccountIndex } from '@app/_eth';
import { HttpGetter } from '@app/_helpers';
import { Web3Service } from '@app/_services/web3.service';

@Injectable({
  providedIn: 'root',
})
export class RegistryService {
  static fileGetter: FileGetter = new HttpGetter();
  private static registry: CICRegistry;
  private static tokenRegistry: TokenRegistry;
  private static accountRegistry: AccountIndex;

  public static async getRegistry(): Promise<CICRegistry> {
    return new Promise(async (resolve, reject) => {
      if (!RegistryService.registry) {
        RegistryService.registry = new CICRegistry(
          Web3Service.getInstance(),
          environment.registryAddress,
          'Registry',
          RegistryService.fileGetter,
          ['../../assets/js/block-sync/data']
        );
        RegistryService.registry.declaratorHelper.addTrust(environment.trustedDeclaratorAddress);
        await RegistryService.registry.load();
        return resolve(RegistryService.registry);
      }
      return resolve(RegistryService.registry);
    });
  }

  public static async getTokenRegistry(): Promise<TokenRegistry> {
    return new Promise(async (resolve, reject) => {
      if (!RegistryService.tokenRegistry) {
        const registry = await RegistryService.getRegistry();
        const tokenRegistryAddress = await registry.getContractAddressByName('TokenRegistry');
        if (!tokenRegistryAddress) {
          return reject('Unable to initialize Token Registry');
        }
        RegistryService.tokenRegistry = new TokenRegistry(tokenRegistryAddress);
        return resolve(RegistryService.tokenRegistry);
      }
      return resolve(RegistryService.tokenRegistry);
    });
  }

  public static async getAccountRegistry(): Promise<AccountIndex> {
    return new Promise(async (resolve, reject) => {
      if (!RegistryService.accountRegistry) {
        const registry = await RegistryService.getRegistry();
        const accountRegistryAddress = await registry.getContractAddressByName('AccountRegistry');

        if (!accountRegistryAddress) {
          return reject('Unable to initialize Account Registry');
        }
        RegistryService.accountRegistry = new AccountIndex(accountRegistryAddress);
        return resolve(RegistryService.accountRegistry);
      }
      return resolve(RegistryService.accountRegistry);
    });
  }
}
