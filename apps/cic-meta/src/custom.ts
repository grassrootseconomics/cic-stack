import {Addressable, mergeKey, Syncable} from "@cicnet/crdt-meta";

class Custom extends Syncable implements Addressable {

    name:	string
    value:	Object

    constructor(name:string, v:Object={}) {
        super('', v);
        Custom.toKey(name).then((cid) => {
            this.id = cid;
            this.name = name;
        });
    }

    public static async toKey(item:string, identifier: string = ':cic.custom') {
        return await mergeKey(Buffer.from(item), Buffer.from(identifier));
    }

    public key(): string {
        return this.id;
    }
}

export {
    Custom,
}
