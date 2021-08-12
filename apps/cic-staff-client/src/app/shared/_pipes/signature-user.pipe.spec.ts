import { SignatureUserPipe } from './signature-user.pipe';

describe('SignatureUserPipe', () => {
  it('create an instance', () => {
    const pipe = new SignatureUserPipe();
    expect(pipe).toBeTruthy();
  });
});
