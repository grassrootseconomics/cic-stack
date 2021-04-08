const fs = require('fs');
const path = require('path');
const http = require('http');

const cic = require('cic-client-meta');

//const conf = JSON.parse(fs.readFileSync('./cic.conf'));

const config = new cic.Config('./config'); 
config.process();
console.log(config);


function sendit(uid, envelope) {
	const d = envelope.toJSON();

	const contentLength = (new TextEncoder().encode(d)).length;
	const opts = {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'Content-Length': contentLength,
			'X-CIC-AUTOMERGE': 'client',

		},
	};
	let url = config.get('META_URL');
	url = url.replace(new RegExp('^(.+://[^/]+)/*$'), '$1/');
	console.log('posting to url: ' + url + uid);
	const req = http.request(url + uid, opts, (res) => {
		res.on('data', process.stdout.write);
		res.on('end', () => {
			console.log('result', res.statusCode, res.headers);
		});
	});
	if (!req.write(d)) {
		console.error('foo', d);
		process.exit(1);
	}
	req.end();
}

function doOne(keystore, filePath) {
	const signer = new cic.PGPSigner(keystore);
	const parts = path.basename(filePath).split('.');
	const ethereum_address = path.basename(parts[0]);

	cic.User.toKey('0x' + ethereum_address).then((uid) => {
		const d = fs.readFileSync(filePath, 'utf-8');
		const o = JSON.parse(d);
		//console.log(o);
		fs.unlinkSync(filePath);

		const s = new cic.Syncable(uid, o);
		s.setSigner(signer);
		s.onwrap = (env) => {
			sendit(uid, env);
		};
		s.sign();
	});
}

const privateKeyPath = path.join(config.get('PGP_EXPORTS_DIR'), config.get('PGP_PRIVATE_KEY_FILE'));
const publicKeyPath = path.join(config.get('PGP_EXPORTS_DIR'), config.get('PGP_PRIVATE_KEY_FILE'));
pk = fs.readFileSync(privateKeyPath);
pubk = fs.readFileSync(publicKeyPath);

new cic.PGPKeyStore(
	config.get('PGP_PASSPHRASE'),
	pk,
	pubk,
	undefined,
	undefined,
	importMeta,
);

const batchSize = 16;
const batchDelay = 1000;
const total = parseInt(process.argv[3]);
const workDir = path.join(process.argv[2], 'meta');
let count = 0;
let batchCount = 0;


function importMeta(keystore) {
	let err;
	let files;

	try {
		err, files = fs.readdirSync(workDir);
	} catch {
		console.error('source directory not yet ready', workDir);
		setTimeout(importMeta, batchDelay, keystore);
		return;
	}
	let limit = batchSize;
	if (files.length < limit) {
		limit = files.length;
	}
	for (let i = 0; i < limit; i++) {
		const file = files[i];
		if (file.substr(-5) != '.json') {
			console.debug('skipping file', file);	
		}
		const filePath = path.join(workDir, file);
		doOne(keystore, filePath);
		count++;
		batchCount++;
		if (batchCount == batchSize) {
			console.debug('reached batch size, breathing');
			batchCount=0;
			setTimeout(importMeta, batchDelay, keystore);
			return;
		}
	}
	if (count == total) {
		return;
	}
	setTimeout(importMeta, 100, keystore);
}
