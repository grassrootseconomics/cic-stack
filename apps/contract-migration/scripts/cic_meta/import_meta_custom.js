const fs = require('fs');
const path = require('path');
const http = require('http');

const cic = require('cic-client-meta');
const vcfp = require('vcard-parser');

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

function doOne(keystore, filePath, identifier) {
	const signer = new cic.PGPSigner(keystore);

	const o = JSON.parse(fs.readFileSync(filePath).toString());
	//const b = Buffer.from(j['vcard'], 'base64');
	//const s = b.toString();
	//const o = vcfp.parse(s);
	//const phone = o.tel[0].value;

	//cic.Phone.toKey(phone).then((uid) => {
	//const o = fs.readFileSync(filePath, 'utf-8');

	const s = new cic.Syncable(identifier, o);
	s.setSigner(signer);
	s.onwrap = (env) => {
		sendit(identifier, env);
	};
	s.sign();
	//});
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
	importMetaCustom,
);

const batchSize = 16;
const batchDelay = 1000;
const total = parseInt(process.argv[3]);
const dataDir = process.argv[2];
const workDir = path.join(dataDir, 'custom/meta');
const userDir = path.join(dataDir, 'custom/new');
let count = 0;
let batchCount = 0;


function importMetaCustom(keystore) {
	let err;
	let files;

	try {
		err, files = fs.readdirSync(workDir);
	} catch {
		console.error('source directory not yet ready', workDir);
		setTimeout(importMetaPhone, batchDelay, keystore);
		return;
	}
	let limit = batchSize;
	if (files.length < limit) {
		limit = files.length;
	}
	for (let i = 0; i < limit; i++) {
		const file = files[i];
		if (file.length < 3) {
			console.debug('skipping file', file);	
			continue;
		}
		//const identifier = file.substr(0,file.length-5);
		const identifier = file;
		const filePath = path.join(workDir, file);
		console.log(filePath);

		//const address = fs.readFileSync(filePath).toString().substring(2).toUpperCase();
		const custom = JSON.parse(fs.readFileSync(filePath).toString());
		const customFilePath = path.join(
			userDir,
			identifier.substring(0, 2),
			identifier.substring(2, 4),
			identifier + '.json',
		);

		doOne(keystore, filePath, identifier);
		fs.unlinkSync(filePath);
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
	setTimeout(importMetaCustom, 100, keystore);
}