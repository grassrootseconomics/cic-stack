// Application imports
import { MutableKeyStore, MutablePgpKeyStore } from '@app/_pgp/pgp-key-store';
import { PGPSigner } from '@app/_pgp/pgp-signer';

const keystore: MutableKeyStore = new MutablePgpKeyStore();

describe('PgpSigner', () => {
  it('should create an instance', () => {
    expect(new PGPSigner(keystore)).toBeTruthy();
  });
});
