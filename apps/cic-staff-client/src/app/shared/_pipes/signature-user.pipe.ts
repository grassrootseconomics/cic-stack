import { Pipe, PipeTransform } from '@angular/core';
import * as openpgp from 'openpgp';
import { asciiToHex } from '@app/_helpers';
import { KeystoreService } from '@app/_services';

@Pipe({
  name: 'signatureUser',
})
export class SignatureUserPipe implements PipeTransform {
  async transform(armoredSignature: string, ...args: unknown[]): Promise<string> {
    const keystore = await KeystoreService.getKeystore();
    const signature = await openpgp.signature.readArmored(armoredSignature);
    const keyId = asciiToHex(signature.packets[0].issuerKeyId.bytes);
    const pubKey = keystore.getPublicKeyForId(keyId);
    if (pubKey) {
      return pubKey.users[0].userId.userid;
    }
    return '';
  }
}
