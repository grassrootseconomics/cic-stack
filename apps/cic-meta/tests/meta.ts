import * as assert from 'assert';
import * as fs from 'fs';
const nock = require('nock');
import {Meta} from "../src";
import {getResponse, metaData, networkErrorResponse, notFoundResponse, putResponse} from "./response";
import {Syncable} from "@cicnet/crdt-meta";

const metaUrl = 'https://meta.dev.grassrootseconomics.net';
const testAddress = '0xc1912fee45d61c87cc5ea59dae31190fffff232d';
const testAddressKey = 'a51472cb4df63b199a4de01335b1b4d1bbee27ff4f03340aa1d592f26c6acfe2';
const testPhone = '+254123456789';
const testPhoneKey = 'be3cc8212b7eb57c6217ddd42230bd8ccd2f01382bf8c1c77d3a683fa5a9bb16';
const testName = 'areas'
const testNameKey = '8f3da0c90ba2b89ff217da96f6088cbaf987a1b58bc33c3a5e526e53cec7cfed';
const testIdentifier = ':cic.area'
const testIdentifierKey = 'da6194e6f33726546e82c328df4c120b844d6427859156518bd600765bf8b2b7';

function readFile(filename) {
    if(!fs.existsSync(filename)) {
        console.error(`File ${filename} not found`);
        return;
    }
    return fs.readFileSync(filename, {encoding: 'utf8', flag: 'r'});
}

const privateKey = readFile('./privatekeys.asc');

describe('meta', () => {
    beforeEach(() => {
        nock(metaUrl)
            .get(`/${testAddressKey}`)
            .reply(200, getResponse);

        nock(metaUrl)
            .get(`/${testPhoneKey}`)
            .reply(200, getResponse);

        nock(metaUrl)
            .get(`/${testAddress}`)
            .reply(404);

        nock(metaUrl)
            .get(`/${testIdentifier}`)
            .replyWithError(networkErrorResponse);

        nock(metaUrl)
            .put(`/${testAddressKey}`)
            .reply(200, putResponse);

        nock(metaUrl)
            .put(`/${testAddress}`)
            .reply(404);

        nock(metaUrl)
            .post('/post')
            .reply(500);
    });

    describe('#get()', () => {
        it('should fetch data from the meta service', async () => {
            const account = await Meta.get(testAddressKey, metaUrl);
            assert.strictEqual(account.toJSON(account), getResponse.payload);
        });

        context('if item is not found', () => {
            it('should respond with an error', async () => {
                const account = await Meta.get(testAddress, metaUrl);
                assert.strictEqual(account, `404: Not Found`);
            });
        });

        context('in case of network error', () => {
            it('should respond with an error', async () => {
                const account = await Meta.get(testIdentifier, metaUrl);
                assert.strictEqual(account, `Request to ${metaUrl}/${testIdentifier} failed. Connection error.`);
            });
        });
    })

    describe('#set()', () => {
        context('object data', () => {
            it('should set data to the meta server', () => {
                const meta = new Meta(metaUrl, privateKey);
                meta.onload = async (status) => {
                    const response = await meta.set(testAddressKey, metaData);
                    assert.strictEqual(response, `${putResponse.status}: ${putResponse.statusText}`);
                }
            });
        });

        context('string data', () => {
            it('should set data to the meta server', () => {
                const meta = new Meta(metaUrl, privateKey);
                meta.onload = async (status) => {
                    const response = await meta.set(testPhoneKey, testAddress);
                    assert.strictEqual(response, `${putResponse.status}: ${putResponse.statusText}`);
                }
            });
        });

        context('in case of network error', () => {
            it('should respond with an error', () => {
                const meta = new Meta(metaUrl, privateKey);
                meta.onload = async (status) => {
                    const response = await meta.set(testIdentifier, metaData);
                    assert.strictEqual(response, `Request to ${metaUrl}/${testIdentifier} failed. Connection error.`);
                }
            });
        });
    });

    describe('#updateMeta()', () => {
        it('should update data in the meta server', async () => {
            const syncable = new Syncable(testAddressKey, metaData);
            const meta = new Meta(metaUrl, privateKey);
            meta.onload = async (status) => {
                const response = await meta.updateMeta(syncable, testAddressKey);
                assert.strictEqual(response, putResponse);
            }
        });

        context('if item is not found', () => {
            it('should respond with an error', () => {
                const syncable = new Syncable(testAddress, metaData);
                const meta = new Meta(metaUrl, privateKey);
                meta.onload = async (status) => {
                    const response = await meta.updateMeta(syncable, testAddress);
                    assert.strictEqual(response, notFoundResponse);
                }
            });
        });
    });

    describe('#wrap()', () => {
        it('should sign a syncable object', function () {
            const syncable = new Syncable(testAddressKey, metaData);
            const meta = new Meta(metaUrl, privateKey);
            meta.onload = async (status) => {
                const response = await meta.wrap(syncable);
                assert.strictEqual(response.toJSON(), getResponse);
            }
        });
    })

    describe('#getIdentifier()', () => {
        context('without type', () => {
            it('should return an identifier', async () => {
                assert.strictEqual(await Meta.getIdentifier(testName), testNameKey);
            });
        });

        context('with user type', () => {
            it('should return an identifier', async () => {
                assert.strictEqual(await Meta.getIdentifier(testAddress, 'user'), testAddressKey);
            });
        });

        context('with phone type', () => {
            it('should return an identifier', async () => {
                assert.strictEqual(await Meta.getIdentifier(testPhone, 'phone'), testPhoneKey);
            });
        });

        context('with custom type', () => {
            it('should return an identifier', async () => {
                assert.strictEqual(await Meta.getIdentifier(testName, 'custom'), testNameKey);
            });
        });

        context('with unrecognised type', () => {
            it('should return an identifier', async () => {
                assert.strictEqual(await Meta.getIdentifier(testName, testIdentifier), testIdentifierKey);
            });
        });
    });
});
