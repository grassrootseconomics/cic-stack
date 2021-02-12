const fs = require('fs');
const path = require('path');
const cic = require('cic-client-meta');
const http = require('http');

//const conf = JSON.parse(fs.readFileSync('./cic.conf'));

const config = new cic.Config('./config'); 
config.process();
console.log(config);

// Stolen from https://coderrocketfuel.com/article/recursively-list-all-the-files-in-a-directory-using-node-js
// Thanks!
const getAllFiles = function(dirPath, arrayOfFiles) {
  files = fs.readdirSync(dirPath)

  arrayOfFiles = arrayOfFiles || []

  files.forEach(function(file) {
        if (fs.statSync(dirPath + "/" + file).isDirectory()) {
      arrayOfFiles = getAllFiles(dirPath + "/" + file, arrayOfFiles)
    } else if (file.substr(-5) == '.json') {
      arrayOfFiles.push(path.join(dirPath, "/", file))
    }
  })

  return arrayOfFiles
}

async function sendit(uid, envelope) {
	const d = envelope.toJSON();

	const opts = {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			'Content-Length': d.length,
			'X-CIC-AUTOMERGE': 'client',

		},
	};
	let url = config.get('META_URL');
	url = url.replace(new RegExp('^(.+://[^/]+)/*$'), '$1/');
	console.debug('url: ' + url);
	const req = http.request(url + uid, opts, (res) => {
		res.on('data', process.stdout.write);
		res.on('end', () => {
			console.log('result', res.statusCode, res.headers);
		});
	});

	req.write(d);
	req.end();
}

function doit(keystore) {
	getAllFiles(process.argv[2]).forEach((filename) => {
		const signer = new cic.PGPSigner(keystore);
		const parts = filename.split('.');
		const uid = path.basename(parts[0]);
		
		const d = fs.readFileSync(filename, 'utf-8');
		const o = JSON.parse(d);
		console.log(o);

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
	doit,
);

