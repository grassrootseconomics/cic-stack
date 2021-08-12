// Core imports
import { TestBed } from '@angular/core/testing';

// Application imports
import { HttpConfigInterceptor } from '@app/_interceptors/http-config.interceptor';

describe('HttpConfigInterceptor', () => {
  beforeEach(() =>
    TestBed.configureTestingModule({
      providers: [HttpConfigInterceptor],
    })
  );

  it('should be created', () => {
    const interceptor: HttpConfigInterceptor = TestBed.inject(HttpConfigInterceptor);
    expect(interceptor).toBeTruthy();
  });
});
