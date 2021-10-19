import * as http from 'http';
import * as fs from 'fs';
import * as path from 'path';

import * as handlers from './handlers';
import { PGPKeyStore, PGPSigner, Config } from '@cicnet/crdt-meta';
import { SqliteAdapter, PostgresAdapter } from '../../src/db';

import { standardArgs } from './args';

let configPath = '/usr/local/etc/cic-meta';

const argv = standardArgs.argv;

if (argv['config'] !== undefined) {
	configPath = argv['config'];
}

const config = new Config(configPath, argv['env-prefix']);
config.process();
console.debug(config.toString());

let fp = path.join(config.get('PGP_EXPORTS_DIR'), config.get('PGP_PUBLICKEY_ACTIVE_FILE'));
const pubksa = fs.readFileSync(fp, 'utf-8');
fp = path.join(config.get('PGP_EXPORTS_DIR'), config.get('PGP_PRIVATEKEY_FILE'));
const pksa = fs.readFileSync(fp, 'utf-8');

const dbConfig = {
	'name': config.get('DATABASE_NAME'),
	'user': config.get('DATABASE_USER'),
	'password': config.get('DATABASE_PASSWORD'),
	'host': config.get('DATABASE_HOST'),
	'port': config.get('DATABASE_PORT'),
	'engine': config.get('DATABASE_ENGINE'),
};
let db = undefined;
if (config.get('DATABASE_ENGINE') == 'sqlite') {
       	db = new SqliteAdapter(dbConfig);
} else if (config.get('DATABASE_ENGINE') == 'postgres')  {
       	db = new PostgresAdapter(dbConfig);
} else {
	throw 'database engine ' + config.get('DATABASE_ENGINE') + 'not implemented';
}


let signer = undefined;
const keystore = new PGPKeyStore(config.get('PGP_PASSPHRASE'), pksa, pubksa, pubksa, pubksa, () => {
	keysLoaded();
});

function keysLoaded() {
	signer = new PGPSigner(keystore);
	prepareServer();
}

async function migrateDatabase(cb) {
	try {
		const sql = "SELECT 1 FROM store;"
		db.query(sql, (e, rs) => {
			if (e === null || e === undefined) {
				cb();
				return;
			}
			console.warn('db check for table "store" fail', e);
			
			console.debug('using schema path', config.get('DATABASE_SCHEMA_SQL_PATH'));
			const sql = fs.readFileSync(config.get('DATABASE_SCHEMA_SQL_PATH'), 'utf-8');
			db.query(sql, (e, rs) => {
				if (e !== undefined && e !== null) {
					console.error('db initialization fail', e);
					return;
				} 
				cb();
			});

		});
	} catch(e) {
		console.warn('table store does not exist', e);
	}
}

async function prepareServer() {
	await migrateDatabase(startServer);
}

async function startServer() {
	http.createServer(processRequest).listen(config.get('SERVER_PORT'));
}

const re_digest = /^\/([a-fA-F0-9]{64})\/?$/;
function parseDigest(url) {
	const digest_test = url.match(re_digest);
	if (digest_test === null) {
		throw 'invalid digest';	
	}
	return digest_test[1].toLowerCase();
}

async function processRequest(req, res) {
	let digest = undefined;
	const headers = {
		"Access-Control-Allow-Origin": "*",
		"Access-Control-Allow-Methods": "OPTIONS, POST, GET, PUT",
		"Access-Control-Max-Age": 2592000, // 30 days
		"Access-Control-Allow-Headers": 'Access-Control-Allow-Origin, Content-Type, x-cic-automerge'
	};

	if (req.method === "OPTIONS") {
		res.writeHead(200, headers);
		res.end();
		return;
	}


	if (!['PUT', 'GET', 'POST'].includes(req.method)) {
		res.writeHead(405, {"Content-Type": "text/plain"});
		res.end();
		return;
	}

	let mod = req.method.toLowerCase() + ":automerge:";
	let modDetail = undefined;
	let immutablePost = false;
	try {
		digest = parseDigest(req.url);
	} catch(e) {
		if (req.url == '/') {
			immutablePost = true;
			modDetail = 'immutable';
		} else {
			console.error('url is not empty (' + req.url + ') and not valid digest error: ' + e)
			res.writeHead(400, {"Content-Type": "text/plain"});
			res.end();
			return;
		}
	}

	if (modDetail === undefined) {
		const mergeHeader = req.headers['x-cic-automerge'];
		switch (mergeHeader) {
			case "client":
				if (immutablePost) {
					res.writeHead(400, 'Valid digest missing', {"Content-Type": "text/plain"});
					res.end();
					return;
				}
				modDetail = "client"; // client handles merges
				break;
			case "server":
				if (immutablePost) {
					res.writeHead(400, 'Valid digest missing', {"Content-Type": "text/plain"});
					res.end();
					return;
				}
				modDetail = "server"; // server handles merges
				break;
			case "immutable":
				modDetail = "immutable"; // no merging, literal immutable content with content-addressing
				break;
			default:
				modDetail = "none"; // merged object only (get only)
		}
	}
	mod += modDetail;


	// handle bigger chunks of data
	let data;
	req.on('data', (d) => {
		if (data === undefined) {
			data = d;
		} else {
			data += d;
		}
	});
	req.on('end', async (d) => {
		console.debug('hedaers ', req.headers);
		let inputContentType = req.headers['content-type'];
		let debugString = 'executing mode ' + mod ;
		if (data !== undefined) {
			debugString += ' for content type ' + inputContentType + ' length ' + data.length;
		}
		console.debug(debugString);
		let content;
		let contentType = 'application/json';
		let statusCode = 200;
		let r:any = undefined;
		try {
			switch (mod) {
				case 'put:automerge:client':
					r = await handlers.handleClientMergePut(data, db, digest, keystore, signer);
					if (r == false) {
						res.writeHead(403, {"Content-Type": "text/plain"});
						res.end();
						return;
					}
					break;

				case 'get:automerge:client':
					content = await handlers.handleClientMergeGet(db, digest, keystore);	
					break;

				case 'post:automerge:server':
					content = await handlers.handleServerMergePost(data, db, digest, keystore, signer);	
					break;

				case 'put:automerge:server':
					r = await handlers.handleServerMergePut(data, db, digest, keystore, signer);	
					if (r == false) {
						res.writeHead(403, {"Content-Type": "text/plain"});
						res.end();
						return;
					}
					break;
				//case 'get:automerge:server':
				//	content = await handlers.handleServerMergeGet(db, digest, keystore);	
				//	break;

				case 'get:automerge:none':
					r = await handlers.handleNoMergeGet(db, digest, keystore);	
					if (r === false) {
						res.writeHead(404, {"Content-Type": "text/plain"});
						res.end();
						return;
					}
					content = r[0];
					contentType = r[1];
					break;

				case 'post:automerge:immutable':
					if (inputContentType === undefined) {
						inputContentType = 'application/octet-stream';
					}
					r = await handlers.handleImmutablePost(data, db, digest, keystore, inputContentType);
					if (r[0]) {
						statusCode = 201;
					}
					content = r[1];
					break;

				default:
					res.writeHead(400, {"Content-Type": "text/plain"});
					res.end();
					return;
			}
		} catch(e) {
			console.error('fail', mod, digest, e);
			res.writeHead(500, {"Content-Type": "text/plain"});
			res.end();
			return;
		}

		if (content === undefined) {
			console.error('empty content', data);
			res.writeHead(404, {"Content-Type": "text/plain"});
			res.end();
			return;
		}

		//let responseContentLength;
		//if (typeof(content) == 'string') {
		//	(new TextEncoder().encode(content)).length;
		//}
		const responseContentLength = content.length;
		res.writeHead(statusCode, {
			"Access-Control-Allow-Origin": "*",
			"Content-Type": contentType,
			"Content-Length": responseContentLength,
		});
		res.write(content);
		res.end();
	});
}
