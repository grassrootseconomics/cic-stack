let xmlhttprequest = require('xhr2');
let moolb = require('moolb');

let xhr = new xmlhttprequest();
xhr.responseType = 'json';
xhr.open('GET', 'http://localhost:5555/tx/0/100');
xhr.addEventListener('load', (e) => {

	d = xhr.response;

	b_one = Buffer.from(d.block_filter, 'base64');
	b_two = Buffer.from(d.blocktx_filter, 'base64');

	for (let i = 0; i < 8192; i++) {
		if (b_two[i] > 0) {
			console.debug('value on', i, b_two[i]);
		}
	}
	console.log(b_one, b_two);

	let f_block = moolb.fromBytes(b_one, d.filter_rounds);
	let f_blocktx = moolb.fromBytes(b_two, d.filter_rounds);
	let a = new ArrayBuffer(8);
	let w = new DataView(a);
	for (let i = 410000; i < 430000; i++) {
		w.setInt32(0, i);
		let r = new Uint8Array(a.slice(0, 4));
		if (f_block.check(r)) {
			for (let j = 0; j < 200; j++) {
				w = new DataView(a);
				w.setInt32(4, j);
				r = new Uint8Array(a);
				if (f_blocktx.check(r)) {
					console.log('true', i, j);
				}
			}
		}
	}
});
let r = xhr.send();
