// Application imports
import { MutablePgpKeyStore } from '@app/_pgp/pgp-key-store';

describe('PgpKeyStore', () => {
  it('should create an instance', () => {
    expect(new MutablePgpKeyStore()).toBeTruthy();
  });
});
