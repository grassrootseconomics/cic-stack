const window = self;

self.importScripts('moolb.js', 'driver.js', 'sync.js', 'web3.min.js');

onmessage = function (o) {
  const filters = [
    bloomFromBytes(o.data.filters[0], o.data.filter_rounds),
    bloomFromBytes(o.data.filters[1], o.data.filter_rounds),
  ];
  const w3 = new Web3(o.data.w3_provider);

  const callback = (o) => {
    this.postMessage(o);
  };
  const s = new Driver(w3, o.data.lo, filters, sync_by_filter, callback);
  let hi = undefined;
  if (o.data.hi > 0) {
    hi = o.data.hi;
  }
  s.start(hi);
};
