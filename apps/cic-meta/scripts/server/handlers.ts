import * as Automerge from 'automerge';
import * as pgp from 'openpgp';

import { Envelope, Syncable } from 'crdt-meta';


function handleNoMergeGet(db, digest, keystore) {
	const sql = "SELECT content FROM store WHERE hash = '" + digest + "'";
	return new Promise<string|boolean>((whohoo, doh) => {
		db.query(sql, (e, rs) => {
			if (e !== null && e !== undefined) {
				doh(e);
				return;
			} else if (rs.rowCount == 0) {
				whohoo(false);
				return;
			}

			const cipherText = rs.rows[0]['content'];
			pgp.message.readArmored(cipherText).then((m) => {
				const opts = {
					message: m,
					privateKeys: [keystore.getPrivateKey()],
				};
				pgp.decrypt(opts).then((plainText) => {
					const o = Syncable.fromJSON(plainText.data);
					const r = JSON.stringify(o.m['data']);
					whohoo(r);
				}).catch((e) => {
					console.error('decrypt', e);
					doh(e);
				});
			}).catch((e) => {
				console.error('message', e);
				doh(e);
			});
		})
	});
}

// TODO: add input for change description
function handleServerMergePost(data, db, digest, keystore, signer) {
	return new Promise<string>((whohoo, doh) => {
		const o = JSON.parse(data);
		const cipherText = handleClientMergeGet(db, digest, keystore).then(async (v) => {
			let e = undefined;
			let s = undefined;
			if (v === undefined) {
				s = new Syncable(digest, o);
				s.onwrap = (e) => {
					whohoo(e.toJSON());
				};
				digest = s.digest();
				s.wrap({
					digest: digest,
				});
			} else {
				e = Envelope.fromJSON(v);
				s = e.unwrap();
				s.replace(o, 'server merge');
				e.set(s);
				s.onwrap = (e) => {
					whohoo(e.toJSON());
				}
				digest = s.digest();
				s.wrap({
					digest: digest,
				});
			}
		});
	});
}

// TODO: this still needs to merge with the stored version
function handleServerMergePut(data, db, digest, keystore, signer) {
	return new Promise<boolean>((whohoo, doh) => {
		const wrappedData = JSON.parse(data);

		if (wrappedData.s === undefined) {
			doh('signature missing');
			return;
		}

		const e = Envelope.fromJSON(wrappedData.m);
		let s = undefined;
		try {
			s = e.unwrap();
		} catch(e) {
			console.error(e)
			whohoo(undefined);
		}
		// TODO: we probably should expose method for replacing the signature, this is too intrusive
		s.m = Automerge.change(s.m, 'sign', (doc) => {
			doc['signature'] = wrappedData.s;
		});
		s.setSigner(signer);
		s.onauthenticate = (v) => {
			console.log('vvv', v);
			if (!v) {
				whohoo(undefined);
				return;
			}
			const opts = {
				message: pgp.message.fromText(s.toJSON()),
				publicKeys: keystore.getEncryptKeys(),
			};
			pgp.encrypt(opts).then((cipherText) => {
				const sql = "INSERT INTO store (owner_fingerprint, hash, content) VALUES ('" + signer.fingerprint() + "', '" + digest + "', '" + cipherText.data + "') ON CONFLICT (hash) DO UPDATE SET content = EXCLUDED.content;";
				db.query(sql, (e, rs) => {
					if (e !== null && e !== undefined) {
						doh(e);
						return;
					}
					whohoo(true);
				});
			});
		};
		s.authenticate(true)
	});
}


function handleClientMergeGet(db, digest, keystore) {
	const sql = "SELECT content FROM store WHERE hash = '" + digest + "'";
	return new Promise<string>((whohoo, doh) => {
		db.query(sql, (e, rs) => {
			console.log('rs', e, rs);
			if (e !== null && e !== undefined) {
				doh(e);
				return;
			} else if (rs.rowCount == 0) { // TODO fix the postgres/sqlite method name issues, this will now break on postgres
				whohoo(undefined);
				return;
			}
			const cipherText = rs.rows[0]['content'];
			pgp.message.readArmored(cipherText).then((m) => {
				const opts = {
					message: m,
					privateKeys: [keystore.getPrivateKey()],
				};
				pgp.decrypt(opts).then((plainText) => {
					const o = Syncable.fromJSON(plainText.data);
					const e = new Envelope(o);
					whohoo(e.toJSON());
				}).catch((e) => {
					console.error('decrypt', e);
					doh(e);
				});
			}).catch((e) => {
				console.error('mesage', e);
				doh(e);
			});
		});
	});
}

// TODO: this still needs to merge with the stored version
function handleClientMergePut(data, db, digest, keystore, signer) {
	return new Promise<boolean>((whohoo, doh) => {
		let s = undefined;
		try {
			const e = Envelope.fromJSON(data);
			s = e.unwrap();
		} catch(e) {
			whohoo(false);
			console.error(e)
			return;
		}

		s.setSigner(signer);
		s.onauthenticate = (v) => {
			if (!v) {
				whohoo(false);
				return;
			}

			handleClientMergeGet(db, digest, keystore).then((v) => {
				if (v !== undefined) {
					const env = Envelope.fromJSON(v);
					s.merge(env.unwrap());
				}
				const opts = {
					message: pgp.message.fromText(s.toJSON()),
					publicKeys: keystore.getEncryptKeys(),
				};
				pgp.encrypt(opts).then((cipherText) => {
					const sql = "INSERT INTO store (owner_fingerprint, hash, content) VALUES ('" + signer.fingerprint() + "', '" + digest + "', '" + cipherText.data + "') ON CONFLICT (hash) DO UPDATE SET content = EXCLUDED.content;";
					db.query(sql, (e, rs) => {
						if (e !== null && e !== undefined) {
							doh(e);
							return;
						}
						whohoo(true);
					});
				}).catch((e) => {
					doh(e);	
				});
			});
		};
		s.authenticate(true)
	});
}

export {
	handleClientMergePut,
	handleClientMergeGet,
	handleServerMergePost,
	handleServerMergePut,
	handleNoMergeGet,
};
