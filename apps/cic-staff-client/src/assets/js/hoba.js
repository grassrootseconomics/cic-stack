export function hobaResult(nonce, kid, challenge, signature) {
  return nonce + '.' + kid + '.' + challenge + '.' + signature;
}

export function hobaToSign(nonce, kid, challenge, realm, origin, alg) {
  var s = '';
  var params = [nonce, alg, origin, realm, kid, challenge];
  for (var i = 0; i < params.length; i++) {
    s += params[i].length + ':' + params[i];
  }
  return s;
}

export function hobaParseChallengeHeader(s) {
  const auth_parts = s.split(' ');
  const auth_pairs = auth_parts[1].split(',');
  let auth_values = {};
  for (var i = 0; i < auth_pairs.length; i++) {
    var auth_kv = auth_pairs[i].split(/^([^=]+)="(.+)"/);
    auth_values[auth_kv[1]] = auth_kv[2];
  }
  const challenge_bytes = atob(auth_values['challenge']);

  return {
    challenge: challenge_bytes,
    realm: auth_values['realm'],
  };
}
