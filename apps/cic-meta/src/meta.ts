import {ArgPair, Envelope, Syncable, MutablePgpKeyStore, PGPSigner} from "@cicnet/crdt-meta";
import {User} from "./user";
import {Phone} from "./phone";
import {Custom} from "./custom";
const fetch = require("node-fetch");

const headers =  {
    'Content-Type': 'application/json;charset=utf-8',
    'x-cic-automerge': 'client'
};
const options = {
    headers: headers,
};

class Meta {
    keystore: MutablePgpKeyStore = new MutablePgpKeyStore();
    signer: PGPSigner = new PGPSigner(this.keystore);
    metaUrl: string;
    private privateKey: string;
    onload: (status: boolean) => void;

    constructor(metaUrl: string, privateKey: any) {
        this.metaUrl = metaUrl;
        this.privateKey = privateKey;
        this.keystore.loadKeyring().then(() => {
            this.keystore.importPrivateKey(privateKey).then(() => this.onload(true));
        });
    }

    async set(identifier: string, data: Object): Promise<any> {
        let syncable: Syncable;
        const response = await Meta.get(identifier, this.metaUrl);
        if (response === `Request to ${this.metaUrl}/${identifier} failed. Connection error.`) {
            return response;
        } else if (typeof response !== "object" || typeof data !== "object") {
            syncable = new Syncable(identifier, data);
            const res = await this.updateMeta(syncable, identifier);
            return `${res.status}: ${res.statusText}`;
        } else {
            syncable = await Meta.get(identifier, this.metaUrl);
            let update: Array<ArgPair> = [];
            for (const prop in data) {
                update.push(new ArgPair(prop, data[prop]));
            }
            syncable.update(update, 'client-branch');
            const res = await this.updateMeta(syncable, identifier);
            return `${res.status}: ${res.statusText}`;
        }
    }

    async updateMeta(syncable: Syncable, identifier: string): Promise<any> {
        const envelope: Envelope = await this.wrap(syncable);
        const reqBody: string = envelope.toJSON();
        const putOptions = {
            method: 'PUT',
            headers: headers,
            body: reqBody
        };
        return await fetch(`${this.metaUrl}/${identifier}`, putOptions).then(async response => {
            if (response.ok) {
                return Promise.resolve({
                    status: response.status,
                    statusText: response.statusText + ', Metadata updated successfully!'
                });
            } else {
                return Promise.reject({
                    status: response.status,
                    statusText: response.statusText
                });
            }
        });
    }

    static async get(identifier: string, metaUrl: string): Promise<any> {
        const response = await fetch(`${metaUrl}/${identifier}`, options).then(response => {
            if (response.ok) {
                return (response.json());
            } else {
                return Promise.reject({
                    status: response.status,
                    statusText: response.statusText
                });
            }
        }).catch(error => {
            if (error.code === 'ECONNREFUSED') {
                return `Request to ${metaUrl}/${identifier} failed. Connection error.`
            }
            return `${error.status}: ${error.statusText}`;
        });
        if (typeof response !== "object") {
            return response;
        }
        return Envelope.fromJSON(JSON.stringify(response)).unwrap();
    }

    static async getIdentifier(name: string, type: string = 'custom'): Promise<string> {
        let identifier: string;
        type = type.toLowerCase();
        if (type === 'user') {
            identifier = await User.toKey(name);
        } else if (type === 'phone') {
            identifier = await Phone.toKey(name);
        } else if (type === 'custom') {
            identifier = await Custom.toKey(name);
        } else {
            identifier = await Custom.toKey(name, type);
        }
        return identifier;
    }

    wrap(syncable: Syncable): Promise<Envelope> {
        return new Promise<Envelope>(async (resolve, reject) => {
            syncable.setSigner(this.signer);
            syncable.onwrap = async (env) => {
                if (env === undefined) {
                    reject();
                    return;
                }
                resolve(env);
            };
            syncable.sign();
        });
    }
}

export {
    Meta,
}
