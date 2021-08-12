import { SafePipe } from './safe.pipe';
import { DomSanitizer } from '@angular/platform-browser';

// tslint:disable-next-line:prefer-const
let sanitizer: DomSanitizer;

describe('SafePipe', () => {
  it('create an instance', () => {
    const pipe = new SafePipe(sanitizer);
    expect(pipe).toBeTruthy();
  });
});
