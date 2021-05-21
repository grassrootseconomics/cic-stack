import { Syncable, Addressable, toAddressKey } from '@cicnet/crdt-meta';

const keySalt = new TextEncoder().encode(':cic.person');
class User extends Syncable implements Addressable {

	address:	string
	firstName: 	string
	lastName:	string

	constructor(address:string, v:Object={}) {
		if (v['user'] === undefined) {
			v['user'] = {
				firstName: '',
				lastName: '',
			}
		}
		User.toKey(address).then((uid) => {
			this.id = uid;
			this.address = address;
		});
		super('', v);
	}

	public static async toKey(address:string) {
		return await toAddressKey(address, ':cic.person');
	}

	public key(): string {
		return this.id;
	}

	public setName(firstName:string, lastName:string) {
		//const fn = new ArgPair('user.firstName', firstName)
		//const ln = new ArgPair('user.lastName', lastName)
		const n = {
			'user': {
				'firstName': firstName,
				'lastName': lastName,
			},
		}
		//this.update([fn, ln], 'update name');
		this.replace(n, 'update name');
	}
}

export { User };
