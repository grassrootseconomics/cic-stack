function fetcher(settings) {
  let xhr = new XMLHttpRequest();
  xhr.responseType = 'json';
  xhr.open('GET', 'http://localhost:5555/tx/0/100');
  xhr.addEventListener('load', async (e) => {
    const d = xhr.response;
    client;

    //const digest = await crypto.subtle.digest('SHA-256', ArrayBuffer.from(d.block_filter))
    //console.log('block filter digest', digest)

    const block_filter_binstr = window.atob(d.block_filter);
    let b_one = new Uint8Array(block_filter_binstr.length);
    b_one.map(function (e, i, v) {
      v[i] = block_filter_binstr.charCodeAt([i]);
    });

    const blocktx_filter_binstr = window.atob(d.blocktx_filter);
    let b_two = new Uint8Array(blocktx_filter_binstr.length);
    b_two.map(function (e, i, v) {
      v[i] = blocktx_filter_binstr.charCodeAt([i]);
    });
    for (let i = 0; i < block_filter_binstr.length; i++) {
      if (b_one[i] > 0) {
        console.debug('blocktx value on', i);
      }
    }

    settings.scanFilter(settings, d.low, d.high, b_one, b_two, d.filter_rounds);
  });
  xhr.send();
}
