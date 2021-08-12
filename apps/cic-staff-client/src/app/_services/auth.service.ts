import { Injectable } from '@angular/core';
import { hobaParseChallengeHeader } from '@src/assets/js/hoba.js';
import { signChallenge } from '@src/assets/js/hoba-pgp.js';
import { environment } from '@src/environments/environment';
import { LoggingService } from '@app/_services/logging.service';
import { MutableKeyStore } from '@app/_pgp';
import { ErrorDialogService } from '@app/_services/error-dialog.service';
import { HttpError, rejectBody } from '@app/_helpers/global-error-handler';
import { Staff } from '@app/_models';
import { BehaviorSubject, Observable } from 'rxjs';
import { KeystoreService } from '@app/_services/keystore.service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  mutableKeyStore: MutableKeyStore;
  trustedUsers: Array<Staff> = [];
  private trustedUsersList: BehaviorSubject<Array<Staff>> = new BehaviorSubject<Array<Staff>>(
    this.trustedUsers
  );
  trustedUsersSubject: Observable<Array<Staff>> = this.trustedUsersList.asObservable();

  constructor(
    private loggingService: LoggingService,
    private errorDialogService: ErrorDialogService
  ) {}

  async init(): Promise<void> {
    this.mutableKeyStore = await KeystoreService.getKeystore();
    if (localStorage.getItem(btoa('CICADA_PRIVATE_KEY'))) {
      await this.mutableKeyStore.importPrivateKey(localStorage.getItem(btoa('CICADA_PRIVATE_KEY')));
    }
  }

  getSessionToken(): string {
    return sessionStorage.getItem(btoa('CICADA_SESSION_TOKEN'));
  }

  setSessionToken(token): void {
    sessionStorage.setItem(btoa('CICADA_SESSION_TOKEN'), token);
  }

  setState(s): void {
    document.getElementById('state').innerHTML = s;
  }

  getWithToken(): Promise<boolean> {
    const sessionToken = this.getSessionToken();
    const headers = {
      Authorization: 'Bearer ' + sessionToken,
      'Content-Type': 'application/json;charset=utf-8',
      'x-cic-automerge': 'none',
    };
    const options = {
      headers,
    };
    return fetch(environment.cicMetaUrl, options).then((response) => {
      if (!response.ok) {
        this.loggingService.sendErrorLevelMessage('failed to get with auth token.', this, {
          error: '',
        });

        return false;
      }
      return true;
    });
  }

  // TODO rename to send signed challenge and set session. Also separate these responsibilities
  sendSignedChallenge(hobaResponseEncoded: any): Promise<any> {
    const headers = {
      Authorization: 'HOBA ' + hobaResponseEncoded,
      'Content-Type': 'application/json;charset=utf-8',
      'x-cic-automerge': 'none',
    };
    const options = {
      headers,
    };
    return fetch(environment.cicMetaUrl, options);
  }

  getChallenge(): Promise<any> {
    return fetch(environment.cicMetaUrl).then((response) => {
      if (response.status === 401) {
        const authHeader: string = response.headers.get('WWW-Authenticate');
        return hobaParseChallengeHeader(authHeader);
      }
    });
  }

  async login(): Promise<boolean> {
    if (this.getSessionToken()) {
      sessionStorage.removeItem(btoa('CICADA_SESSION_TOKEN'));
    }
    const o = await this.getChallenge();

    const r = await signChallenge(
      o.challenge,
      o.realm,
      environment.cicMetaUrl,
      this.mutableKeyStore
    );

    const tokenResponse = await this.sendSignedChallenge(r).then((response) => {
      const token = response.headers.get('Token');
      if (token) {
        return token;
      }
      if (response.status === 401) {
        throw new HttpError('You are not authorized to use this system', response.status);
      }
      if (!response.ok) {
        throw new HttpError('Unknown error from authentication server', response.status);
      }
    });

    if (tokenResponse) {
      this.setSessionToken(tokenResponse);
      // this.setState('Click button to log in');
      return true;
    }
    return false;
  }

  loginView(): void {
    document.getElementById('one').style.display = 'none';
    document.getElementById('two').style.display = 'block';
    this.setState('Click button to log in with PGP key ' + this.mutableKeyStore.getPrivateKeyId());
  }

  /**
   * @throws
   * @param privateKeyArmored - Private key.
   */
  async setKey(privateKeyArmored): Promise<boolean> {
    try {
      const isValidKeyCheck = await this.mutableKeyStore.isValidKey(privateKeyArmored);
      if (!isValidKeyCheck) {
        throw Error('The private key is invalid');
      }
      // TODO leaving this out for now.
      // const isEncryptedKeyCheck = await this.mutableKeyStore.isEncryptedPrivateKey(privateKeyArmored);
      // if (!isEncryptedKeyCheck) {
      //   throw Error('The private key doesn\'t have a password!');
      // }
      const key = await this.mutableKeyStore.importPrivateKey(privateKeyArmored);
      localStorage.setItem(btoa('CICADA_PRIVATE_KEY'), privateKeyArmored);
    } catch (err) {
      this.loggingService.sendErrorLevelMessage(
        `Failed to set key: ${err.message || err.statusText}`,
        this,
        { error: err }
      );
      this.errorDialogService.openDialog({
        message: `Failed to set key: ${err.message || err.statusText}`,
      });
      return false;
    }
    this.loginView();
    return true;
  }

  logout(): void {
    sessionStorage.removeItem(btoa('CICADA_SESSION_TOKEN'));
    localStorage.removeItem(btoa('CICADA_PRIVATE_KEY'));
    window.location.reload();
  }

  addTrustedUser(user: Staff): void {
    const savedIndex = this.trustedUsers.findIndex((staff) => staff.userid === user.userid);
    if (savedIndex === 0) {
      return;
    }
    if (savedIndex > 0) {
      this.trustedUsers.splice(savedIndex, 1);
    }
    this.trustedUsers.unshift(user);
    this.trustedUsersList.next(this.trustedUsers);
  }

  getTrustedUsers(): void {
    this.mutableKeyStore.getPublicKeys().forEach((key) => {
      this.addTrustedUser(key.users[0].userId);
    });
  }

  async getPublicKeys(): Promise<any> {
    return new Promise((resolve, reject) => {
      fetch(environment.publicKeysUrl).then((res) => {
        if (!res.ok) {
          // TODO does angular recommend an error interface?
          return reject(rejectBody(res));
        }
        return resolve(res.text());
      });
    });
  }

  getPrivateKey(): any {
    return this.mutableKeyStore.getPrivateKey();
  }

  getPrivateKeyInfo(): any {
    return this.getPrivateKey().users[0].userId;
  }
}
