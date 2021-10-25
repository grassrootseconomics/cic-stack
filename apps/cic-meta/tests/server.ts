import assert = require('assert');
import fs = require('fs');
import pgp = require('openpgp');
import sqlite = require('sqlite3');

import * as handlers from '../scripts/server/handlers';
import { Envelope, Syncable, ArgPair, PGPKeyStore, PGPSigner, KeyStore, Signer } from '@cicnet/crdt-meta';
import { SqliteAdapter } from '../src/db';

const hashOfFoo = '2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae';

function createKeystore() {
	const pksa = fs.readFileSync(__dirname + '/privatekeys.asc', 'utf-8');
	const pubksa = fs.readFileSync(__dirname + '/publickeys.asc', 'utf-8');
	return new Promise<PGPKeyStore>((whohoo, doh) => {
		let keystore = undefined;
		try {
			keystore = new PGPKeyStore('merman', pksa, pubksa, pubksa, pubksa, () => {
				whohoo(keystore);
			});
		} catch(e) {
			doh(e);
		}
		if (keystore === undefined) {
			doh();
		}
	});
}

function createDatabase(sqlite_file:string):Promise<any> {
	try {
		fs.unlinkSync(sqlite_file);
	} catch {
	}
	return new Promise((whohoo, doh) => {
		//const db = new sqlite.Database(sqlite_file, (e) => {
		const dbconf = {
			name: sqlite_file,
			port: undefined,
			host: undefined,
			user: undefined,
			password: undefined,
		}
		const db = new SqliteAdapter(dbconf);//, (e) => {
//			if (e) {
//				doh(e);
//				return;
//			}
		// get this from real sql files sources
			const sql = `CREATE TABLE store (
id integer primary key autoincrement,
owner_fingerprint text default null,
hash char(64) not null unique,
content text not null,
mime_type text default null
);
`

			console.log(sql);
			db.query(sql, (e) => {
				if (e) {
					doh(e);
					return;
				}
				whohoo(db);
			});
//		});
	});
}

function wrap(s:Syncable, signer:Signer) {
	return new Promise<Envelope>((whohoo, doh) => {
		s.setSigner(signer);
		s.onwrap = async (env) => {
			if (env === undefined) {
				doh();
				return;
			}
			whohoo(env);
		}
		s.sign();
	});
}

async function signData(d:string, keyStore:KeyStore) {
	const digest = await pgp.message.fromText(d);
	const opts = {
		message: digest,
		privateKeys: [keyStore.getPrivateKey()],
		detached: true,
	};
	const signature = await pgp.sign(opts);
	return {
		data: signature.signature,
		engine: 'pgp',
		algo: 'sha256',
		digest: d,
	};
}

describe('server', async () => {
	await it('put_client_then_retrieve', async () => {
		const keystore = await createKeystore();

		const signer = new PGPSigner(keystore);

		const digest = 'deadbeef';
		const s = new Syncable(digest, {
			bar: 'baz',
		});
		
		const db = await createDatabase(__dirname + '/db.one.sqlite');

		let env = await wrap(s, signer);
		let j = env.toJSON();
		const content = await handlers.handleClientMergePut(j, db, digest, keystore, signer);
		assert(content); // true-ish
		console.debug('content', content);

		let v = await handlers.handleNoMergeGet(db, digest, keystore);
		if (v === false) {
			db.close();
			assert.fail('');
		}
		db.close();
		return;

		v = await handlers.handleClientMergeGet(db, digest, keystore);
		if (v === false) {
			db.close();
			assert.fail('');
		}

		db.close();
	});

	await it('client_merge', async () => {
		const keystore = await createKeystore();
		const signer = new PGPSigner(keystore);

		const db = await createDatabase(__dirname + '/db.two.sqlite');

		// create new, sign, wrap
		const digest = 'deadbeef';
		let s = new Syncable(digest, {
			bar: 'baz',
		});
		await wrap(s, signer)

		// create client branch, sign, wrap, and serialize
		let update = new ArgPair('baz', 666)
		s.update([update], 'client branch');
		let env = await wrap(s, signer)
		const j_client = env.toJSON();

		// create server branch, sign, wrap, and serialize
		update = new ArgPair('baz', [1,2,3]);
		s.update([update], 'client branch');
		env = await wrap(s, signer)
		const j_server = env.toJSON();

		assert.notDeepEqual(j_client, j_server);

		let v = await handlers.handleClientMergePut(j_server, db, digest, keystore, signer);
		assert(v); // true-ish

		v = await handlers.handleClientMergePut(j_client, db, digest, keystore, signer);
		assert(v); // true-ish
		
		const j = await handlers.handleClientMergeGet(db, digest, keystore);

		env = Envelope.fromJSON(j);
		s = env.unwrap();
		
		db.close();
	});

	await it('server_merge', async () => {
		const keystore = await createKeystore();
		const signer = new PGPSigner(keystore);

		const db = await createDatabase(__dirname + '/db.three.sqlite');

		const digest = 'deadbeef';
		let s = new Syncable(digest, {
			bar: 'baz',
		});
		let env = await wrap(s, signer)
		let j:any = env.toJSON();

		let v = await handlers.handleClientMergePut(j, db, digest, keystore, signer);
		assert(v); // true-ish

		j = await handlers.handleNoMergeGet(db, digest, keystore);
		assert(v); // true-ish

		let o = JSON.parse(j[0]);
		o.bar = 'xyzzy';
		j = JSON.stringify(o);

		let signMaterial = await handlers.handleServerMergePost(j, db, digest, keystore, signer);
		assert(signMaterial)

		env = Envelope.fromJSON(signMaterial);
		const w = env.unwrap();

		console.log('jjjj', w, env);

		const signedData = await signData(w.m.signature.digest, keystore);

		o = {
			'm': env,
			's': signedData,
		}
		j = JSON.stringify(o);

		v = await handlers.handleServerMergePut(j, db, digest, keystore, signer);
		assert(v);

		j = await handlers.handleNoMergeGet(db, digest, keystore);
		assert(j); // true-ish
		o = JSON.parse(j[0]);
		console.log(o);

		db.close();
	});

//	await it('server_merge', async () => {
//		const keystore = await createKeystore();
//		const signer = new PGPSigner(keystore);
//
//		const db = await createDatabase(__dirname + '/db.three.sqlite');
//
//		const digest = 'deadbeef';
//		let s = new Syncable(digest, {
//			bar: 'baz',
//		});
//		let env = await wrap(s, signer)
//		let j:any = env.toJSON();
//
//		let v = await handlers.handleClientMergePut(j, db, digest, keystore, signer);
//		assert(v); // true-ish
//
//		j = await handlers.handleNoMergeGet(db, digest, keystore);
//		assert(v); // true-ish
//
//		let o = JSON.parse(j);
//		o.bar = 'xyzzy';
//		j = JSON.stringify(o);
//
//		let signMaterial = await handlers.handleServerMergePost(j, db, digest, keystore, signer);
//		assert(signMaterial)
//
//		env = Envelope.fromJSON(signMaterial);
//
//		console.log('envvvv', env);
//
//		const signedData = await signData(env.o['digest'], keystore);
//		console.log('signed', signedData);
//
//		o = {
//			'm': env,
//			's': signedData,
//		}
//		j = JSON.stringify(o);
//		console.log(j);
//
//		v = await handlers.handleServerMergePut(j, db, digest, keystore, signer);
//		assert(v);
//
//		j = await handlers.handleNoMergeGet(db, digest, keystore);
//		assert(j); // true-ish
//		o = JSON.parse(j);
//		console.log(o);
//
//		db.close();
//	});
//


	await it('server_merge_empty', async () => {
		const keystore = await createKeystore();
		const signer = new PGPSigner(keystore);

		const db = await createDatabase(__dirname + '/db.three.sqlite');

		const digest = '0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef';
		let o:any = {
			foo: 'bar',
			xyzzy: 42,
		}
		let j:any = JSON.stringify(o);

		let signMaterial = await handlers.handleServerMergePost(j, db, digest, keystore, signer);
		assert(signMaterial)

		const env = Envelope.fromJSON(signMaterial);

		console.log('envvvv', env);

		const signedData = await signData(env.o['digest'], keystore);
		console.log('signed', signedData);

		o = {
			'm': env,
			's': signedData,
		}
		j = JSON.stringify(o);
		console.log(j);

		let v = await handlers.handleServerMergePut(j, db, digest, keystore, signer);
		assert(v);

		j = await handlers.handleNoMergeGet(db, digest, keystore);
		assert(j); // true-ish
		o = JSON.parse(j[0]);
		console.log(o);

		db.close();
	});

	await it('immutable_nodigest', async() => {
		const keystore = await createKeystore();
		const db = await createDatabase(__dirname + '/db.three.sqlite');

		const s:string = 'foo';
		let r;
		r = await handlers.handleImmutablePost(s, db, undefined, keystore, 'text/plain');
		assert(r[0]);
		assert(hashOfFoo == r[1]);

		r = await handlers.handleImmutablePost(s, db, undefined, keystore, 'text/plain');
		assert(!r[0]);
		assert(hashOfFoo == r[1]);

		const b:Uint8Array = new TextEncoder().encode(s);
		r = await handlers.handleImmutablePost(b, db, undefined, keystore, 'text/plain');
		assert(!r[0]);
		assert(hashOfFoo == r[1]);
	});

	await it('immutable_digest', async() => {
		const keystore = await createKeystore();
		const db = await createDatabase(__dirname + '/db.three.sqlite');

		const s:string = 'foo';
		const b:Uint8Array = new TextEncoder().encode(s);
		let r;
		r = await handlers.handleImmutablePost(b, db, hashOfFoo, keystore, 'application/octet-stream');
		assert(r[0]);
		assert(hashOfFoo == r[1]);

		r = await handlers.handleImmutablePost(b, db, hashOfFoo, keystore, 'application/octet-stream');
		assert(!r[0]);
		assert(hashOfFoo == r[1]);

		r = await handlers.handleImmutablePost(s, db, hashOfFoo, keystore, 'text/plain');
		assert(!r[0]);
		assert(hashOfFoo == r[1]);
	});
});

