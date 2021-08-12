// Application imports
import { TokenRegistry } from '@app/_eth/token-registry';
import { environment } from '@src/environments/environment';

describe('TokenRegistry', () => {
  it('should create an instance', () => {
    expect(new TokenRegistry(environment.registryAddress)).toBeTruthy();
  });
});
