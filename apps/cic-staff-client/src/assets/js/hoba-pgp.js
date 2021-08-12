import { hobaResult, hobaToSign } from '@src/assets/js/hoba.js';

const alg = '969';

export async function signChallenge(challenge, realm, origin, keyStore) {
  const fingerprint = keyStore.getFingerprint();
  const nonce_array = new Uint8Array(32);
  crypto.getRandomValues(nonce_array);

  const kid_array = fingerprint;

  const a_kid = btoa(String.fromCharCode.apply(null, kid_array));
  const a_nonce = btoa(String.fromCharCode.apply(null, nonce_array));
  const a_challenge = btoa(challenge);
  const message = hobaToSign(a_nonce, a_kid, a_challenge, realm, origin, alg);

  const signature = await keyStore.sign(message);
  const a_signature = btoa(signature);

  const result = hobaResult(a_nonce, a_kid, a_challenge, a_signature);
  return result;
}
