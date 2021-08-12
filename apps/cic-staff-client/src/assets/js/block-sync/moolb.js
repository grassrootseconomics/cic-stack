let crypto = undefined;

(function () {
  if (typeof module !== 'undefined' && typeof exports !== 'undefined') {
    let nodeCrypto = require('crypto');
    function hashWrapper(nodeCrypto, alg) {
      this.alg = alg;
      this.crypto = nodeCrypto.createHash(alg);
    }
    hashWrapper.prototype.update = function (d) {
      this.crypto.update(d);
    };
    hashWrapper.prototype.digest = async function () {
      z = this.crypto.digest(this.data);
      return new Uint8Array(z);
    };

    function cryptoWrapper(nodeCrypto) {
      this.crypto = nodeCrypto;
    }
    cryptoWrapper.prototype.createHash = function (alg) {
      return new hashWrapper(this.crypto, alg);
    };
    module.exports = {
      Bloom: Bloom,
      fromBytes: fromBytes,
    };
    crypto = new cryptoWrapper(nodeCrypto);
  } else {
    function hashWrapper(webCrypto, alg) {
      this.alg = alg;
      this.crypto = webCrypto;
      this.data = undefined;
    }
    hashWrapper.prototype.update = function (d) {
      if (this.data != undefined) {
        throw 'cannot append';
      }
      this.data = d;
    };
    hashWrapper.prototype.digest = async function () {
      z = await this.crypto.subtle.digest('SHA-256', this.data);
      return new Uint8Array(z);
    };

    function cryptoWrapper(webCrypto) {
      this.crypto = webCrypto;
    }
    cryptoWrapper.prototype.createHash = function (alg) {
      return new hashWrapper(this.crypto, alg);
    };

    crypto = new cryptoWrapper(window.crypto);
    window.Bloom = Bloom;
    window.bloomFromBytes = fromBytes;
  }
})();

// block numbers 6000000
// false positive probability 2%
//
// m = ceil((n * log(p)) / log(1 / pow(2, log(2))));
// m = ceil((6000000 * log(0.1)) / log(1 / pow(2, log(2))))
// = 3917675

// Creates a new bloom object.
// \param size of filter in bits, aligned to byte boundary
// \param number of rounds to hash
// \param hasher function, which must take two Uint8Array parameters 'data' and 'salt'. If not sef, hashBloomDefault will be used.
function Bloom(bits, rounds, hasher) {
  this.bits = bits;
  this.bytes = parseInt(bits / 8, 10);
  this.rounds = rounds;
  if (this.hasher === undefined) {
    this.hasher = hashBloomDefault;
  }
  if (this.bytes * 8 != this.bits) {
    console.error('number of bits must be on byte boundary');
    return false;
  } else {
    this.filter = new Uint8Array(this.bytes);
  }
}

// add entry to bloom filter
// \param value to add
Bloom.prototype.add = async function (v) {
  let a = new ArrayBuffer(v.byteLength + 4);
  let iw = new DataView(a);
  for (let i = 0; i < v.byteLength; i++) {
    iw.setUint8(i, v[i]);
  }
  console.log(iw, v);
  for (var i = 0; i < this.rounds; i++) {
    iw.setInt32(v.byteLength, i);
    let result = await this.hasher(iw);
    let resultHex = Array.prototype.map
      .call(new Uint8Array(result), (x) => ('00' + x.toString(16)).slice(-2))
      .join('');
    let resultInt = parseInt(BigInt('0x' + resultHex) % BigInt(this.bits), 10);
    let bytepos = parseInt(resultInt / 8, 10);
    let bitpos = parseInt(resultInt, 10) % 8;
    this.filter[bytepos] |= 1 << bitpos;
    //console.log("setpos ", bytepos, bitpos);
  }
};

// checks if the block number has been added to the bloom filter
// \param value to check for
// \return false if not found in filter
Bloom.prototype.check = async function (v) {
  let a = new ArrayBuffer(v.byteLength + 4);
  let iw = new DataView(a);
  for (let i = 0; i < v.byteLength; i++) {
    iw.setUint8(i, v[i]);
  }
  for (let i = 0; i < this.rounds; i++) {
    iw.setInt32(v.byteLength, i);
    let result = await this.hasher(iw);
    //console.log('result', result);
    let resultHex = Array.prototype.map
      .call(new Uint8Array(result), (x) => ('00' + x.toString(16)).slice(-2))
      .join('');
    let resultInt = parseInt(BigInt('0x' + resultHex) % BigInt(this.bits), 10);
    let bytepos = parseInt(resultInt / 8, 10);
    //console.log("setpos ", bytepos, resultInt % 8);
    if (this.filter[bytepos] === undefined) {
      console.error(
        'byte pos ' + bytepos + ' is undefined (filter length ' + this.filter.byteLength + ')'
      );
      return false;
    } else {
      let test = 1 << (0xff & resultInt % 8);
      if ((this.filter[bytepos] & test) == 0) {
        return false;
      }
    }
  }
  return true;
};

// return the verbatim filter
// \return Uint8Array filter
Bloom.prototype.bytes = function () {
  return this.filter;
};

// Default hashing function used in Bloom.add() - sha256
// \param data to insert in filter
// \param salt, typically a sequence number
// \return Uint8Array digest
async function hashBloomDefault(data, salt) {
  let h = crypto.createHash('sha256');
  h.update(data);
  z = await h.digest();
  return Uint8Array.from(z);
}

function fromBytes(bytes, rounds, hasher) {
  let bits = bytes.byteLength * 8;
  let b = new Bloom(bits, rounds, hasher);
  b.filter = bytes;
  return b;
}
