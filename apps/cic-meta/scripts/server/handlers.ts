import * as Automerge from 'automerge';
import * as pgp from 'openpgp';
import * as crypto from 'crypto';

import { Envelope, Syncable, bytesToHex } from '@cicnet/crdt-meta';


function handleNoMergeGet(db, digest, keystore) {
	const sql = "SELECT owner_fingerprint, content, mime_type FROM store WHERE hash = '" + digest + "'";
	return new Promise<any>((whohoo, doh) => {
		db.query(sql, (e, rs) => {
			if (e !== null && e !== undefined) {
				doh(e);
				return;
			} else if (rs.rowCount == 0) {
				whohoo(false);
				return;
			}

			const immutable = rs.rows[0]['owner_fingerprint'] == undefined;
			let mimeType;
			if (immutable) {
				if (rs.rows[0]['mime_type'] === undefined) {
					mimeType = 'application/octet-stream';
				} else {
					mimeType = rs.rows[0]['mime_type'];
				}
			} else {
				mimeType = 'application/json';
			}

			const cipherText = rs.rows[0]['content'];
			pgp.message.readArmored(cipherText).then((m) => {
				const opts = {
					message: m,
					privateKeys: [keystore.getPrivateKey()],
					format: 'binary',
				};
				pgp.decrypt(opts).then((plainText) => {
					console.debug('immutable ', rs.rows[0]['owner_fingerprint'], immutable);
					let r;
				     	if (immutable) {
						r = plainText.data;
					} else {
						mimeType = 'application/json';
						const d = new TextDecoder().decode(plainText.data);
						const o = Syncable.fromJSON(d);
						r = JSON.stringify(o.m['data']);
					}
					whohoo([r, mimeType]);
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
					let d;
					if (typeof(plainText.data) == 'string') {
						d = plainText.data;
					} else {
						d = new TextDecoder().decode(plainText.data);
					}
					const o = Syncable.fromJSON(d);
					const e = new Envelope(o);
					whohoo(e.toJSON());
				}).catch((e) => {
					console.error('decrypt', e);
					doh(e);
				});
			}).catch((e) => {
				console.error('message', e);
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


function handleImmutablePost(data, db, digest, keystore, contentType) {
	return new Promise<Array<string|boolean>>((whohoo, doh) => {
		let data_binary = data;
		const h = crypto.createHash('sha256');
		h.update(data_binary);
		const z = h.digest();
		const r = bytesToHex(z);

		if (digest) {
			if (r != digest) {
				doh('hash mismatch: ' + r + ' != ' +  digest);
				return;
			}
		} else {
			digest = r;
			console.debug('calculated digest ' + digest);
		}

		handleNoMergeGet(db, digest, keystore).then((haveDigest) => {
			if (haveDigest !== false) {
				whohoo([false, digest]);
				return;
			}
			let message;
			if (typeof(data) == 'string') {
				data_binary = new TextEncoder().encode(data);
				message = pgp.message.fromText(data);
			} else {
				message = pgp.message.fromBinary(data);
			}

					const opts = {
				message: message,
				publicKeys: keystore.getEncryptKeys(),
			};
			pgp.encrypt(opts).then((cipherText) => {
				const sql = "INSERT INTO store (hash, content, mime_type) VALUES ('" + digest + "', '" + cipherText.data + "', '" + contentType + "') ON CONFLICT (hash) DO UPDATE SET content = EXCLUDED.content;";
				db.query(sql, (e, rs) => {
					if (e !== null && e !== undefined) {
						doh(e);
						return;
					}
					whohoo([true, digest]);
				});
			}).catch((e) => {
				doh(e);	
			});
		}).catch((e) => {
			doh(e);	
		});
	});
}

export {
	handleClientMergePut,
	handleClientMergeGet,
	handleServerMergePost,
	handleServerMergePut,
	handleNoMergeGet,
	handleImmutablePost,
};
