if (typeof module != 'undefined') {
  module.exports = {
    by_filter: sync_by_filter,
    by_filter_block: sync_by_filter_block,
  };
}

function sync_by_filter_block(block, count, buf, bloom_blocktx, result_callback) {
  for (let j = 0; j < count; j++) {
    let w = new DataView(buf);
    w.setInt32(4, j);
    const r = new Uint8Array(buf);
    bloom_blocktx.check(r).then(function (ok) {
      if (ok) {
        console.debug('match in block ' + block + ' tx ' + j);
        result_callback(block, j);
      }
    });
  }
}

function sync_by_filter(lo, hi, bloom_block, bloom_blocktx, tx_count_getter, result_callback) {
  for (let i = lo; i <= hi; i++) {
    let a = new ArrayBuffer(8);
    let w = new DataView(a);
    w.setInt32(0, i);
    const r = new Uint8Array(a.slice(0, 4));
    bloom_block.check(r).then(function (ok) {
      if (ok) {
        console.debug('match in block ' + i);
        tx_count_getter(i)
          .then(function (n) {
            sync_by_filter_block(i, n, a, bloom_blocktx, result_callback);
          })
          .catch((e) => {
            console.error('get count fail', e);
          });
      }
    });
  }
}
