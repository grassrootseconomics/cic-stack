import { ArgPair, Syncable } from '../sync';
import { Addressable, mergeKey } from '../digest';

class Phone extends Syncable implements Addressable {

	address:	string
	value:		number

	constructor(address:string, v:string) {
		const o = {
			msisdn: v,
		}
		super('', o);
		Phone.toKey(v).then((phid) => {
			this.id = phid;	
			this.address = address;
		});
	}

	public static async toKey(msisdn:string) {
		return await mergeKey(Buffer.from(msisdn), Buffer.from(':cic.phone'));
	}

	public key(): string {
		return this.id;
	}
}

export {
	Phone,
}
