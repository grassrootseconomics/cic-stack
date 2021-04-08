import { ArgPair, Syncable } from '../sync';
import { Addressable, addressToBytes, bytesToHex, toKey } from '../digest';

class Phone extends Syncable implements Addressable {

	address:	string
	value:		number

	constructor(address:string, v:number) {
		const o = {
			msisdn: v,
		}
		super('', o);
		Phone.toKey(v).then((phid) => {
			this.id = phid;	
			this.address = address;
		});
	}

	public static async toKey(msisdn:number) {
		return await toKey(msisdn.toString(), ':cic.phone');
	}

	public key(): string {
		return this.id;
	}
}

export {
	Phone,
}
