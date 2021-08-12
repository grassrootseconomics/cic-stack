import { TestBed } from '@angular/core/testing';

import { ConnectionInterceptor } from './connection.interceptor';

describe('ConnectionInterceptor', () => {
  beforeEach(() =>
    TestBed.configureTestingModule({
      providers: [ConnectionInterceptor],
    })
  );

  it('should be created', () => {
    const interceptor: ConnectionInterceptor = TestBed.inject(ConnectionInterceptor);
    expect(interceptor).toBeTruthy();
  });
});
