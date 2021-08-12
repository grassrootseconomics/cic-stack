import { TestBed } from '@angular/core/testing';

import { TokenService } from '@app/_services/token.service';

describe('TokenService', () => {
  let service: TokenService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(TokenService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('should return token for available token', () => {
    expect(service.getTokenBySymbol('RSV')).toEqual({ name: 'Reserve', symbol: 'RSV' });
  });

  it('should not return token for unavailable token', () => {
    expect(service.getTokenBySymbol('ABC')).toBeUndefined();
  });
});
