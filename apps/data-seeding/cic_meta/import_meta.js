const fs = require('fs');
const path = require('path');
const http = require('http');

const cic = require('@cicnet/cic-client-meta');
const crdt = require('@cicnet/crdt-meta');

//const conf = JSON.parse(fs.readFileSync('./cic.conf'));

const config = new crdt.Config('./config');
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
        if (!res.complete) {
            console.log('The connection was terminated while the message was being sent.')
        }
			console.log('result', res.statusCode, res.headers);
		});
	});
  req.on('error', (err) => {
      console.log('ERROR when talking to meta', err)
  })
  req.write(d)
	req.end();
}

function doOne(keystore, filePath) {
	const signer = new crdt.PGPSigner(keystore);
	const parts = path.basename(filePath).split('.');
	const ethereum_address = path.basename(parts[0]);

	cic.User.toKey('0x' + ethereum_address).then((uid) => {
		const d = fs.readFileSync(filePath, 'utf-8');
		const o = JSON.parse(d);
		//console.log(o);
		fs.unlinkSync(filePath);

		const s = new crdt.Syncable(uid, o);
		s.setSigner(signer);
		s.onwrap = (env) => {
      console.log(`Sending uid: ${uid} and env: ${env} to meta`)
			sendit(uid, env);
		};
		s.sign();
	});
}

const privateKeyPath = path.join(config.get('PGP_EXPORTS_DIR'), config.get('PGP_PRIVATE_KEY_FILE'));
const publicKeyPath = path.join(config.get('PGP_EXPORTS_DIR'), config.get('PGP_PRIVATE_KEY_FILE'));
pk = fs.readFileSync(privateKeyPath);
pubk = fs.readFileSync(publicKeyPath);

new crdt.PGPKeyStore(
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
  console.log('Running importMeta....')
	let err;
	let files;

	try {
		files = fs.readdirSync(workDir);
	} catch (err) {
		console.error('source directory not yet ready', workDir, 'reason: ', err);
		setTimeout(importMeta, batchDelay, keystore);
		return;
	}
  console.log(`Trying to read ${files.length} files`)
  if (files === 0) {
    console.log(`ERROR did not find any files under ${workDir}. \nLooks like there is no work for me, bailing!`)
    process.exit(1)
  }
	let limit = batchSize;
	if (files.length < limit) {
		limit = files.length;
	}
	for (let i = 0; i < limit; i++) {
		const file = files[i];
		if (file.substr(-5) != '.json') {
			console.debug('skipping file', file);	
			continue;
		}
		const filePath = path.join(workDir, file);
		doOne(keystore, filePath);
		count++;
		batchCount++;
    //console.log('done one', count, batchCount)
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
