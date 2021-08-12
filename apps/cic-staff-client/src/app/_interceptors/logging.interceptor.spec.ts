// Core imports
import { TestBed } from '@angular/core/testing';

// Application imports
import { LoggingInterceptor } from '@app/_interceptors/logging.interceptor';

describe('LoggingInterceptor', () => {
  beforeEach(() =>
    TestBed.configureTestingModule({
      providers: [LoggingInterceptor],
    })
  );

  it('should be created', () => {
    const interceptor: LoggingInterceptor = TestBed.inject(LoggingInterceptor);
    expect(interceptor).toBeTruthy();
  });
});
