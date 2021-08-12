if (typeof module != 'undefined') {
  module.exports = {
    Driver: Driver,
  };
}

function Driver(w3, lo, filters, syncer, callback) {
  this.w3 = w3;
  this.lo = lo;
  this.hi = undefined;
  this.filters = filters;
  this.syncer = syncer;
  this.callback = callback;
}

Driver.prototype.start = function (hi) {
  const self = this;

  if (hi !== undefined) {
    self.sync(hi);
    return;
  }
  self.w3.eth
    .getBlockNumber()
    .then(function (n) {
      self.sync(n);
    })
    .catch((e) => {
      console.error('blocknumber fail', e);
    });
};

Driver.prototype.sync = function (n) {
  const self = this;

  self.hi = n;

  const countGetter = async (b) => {
    return await self.getCount(b);
  };

  const processor = async (b, t) => {
    return await self.process(b, t);
  };
  self.syncer(self.lo, self.hi, self.filters[0], self.filters[1], countGetter, processor);
};

Driver.prototype.process = function (b, t) {
  const self = this;

  self.w3.eth
    .getTransactionFromBlock(b, t)
    .then((t) => {
      self.w3.eth
        .getTransactionReceipt(t.hash)
        .then((r) => {
          console.log('Receipt: ', r);
          self.callback(r);
        })
        .catch((e) => {
          console.error('fail get receipt', e);
        });
    })
    .catch(function (e) {
      //this.postMessage(['failed getTransactionFromBlock(' + b + ', ' + t + ')']);
      self.callback([undefined]);
      console.error('failed getTransactionFromBlock(' + b + ', ' + t + ')');
    });
};

Driver.prototype.getCount = async function (b) {
  const self = this;

  const n = await self.w3.eth.getBlockTransactionCount(b);
  return n;
};
