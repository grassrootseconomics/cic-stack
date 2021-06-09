import * as assert from 'assert';
import {Custom} from "../src";

const testName = 'areas';
const testObject = {
    area: ['Nairobi', 'Mombasa', 'Kilifi']
}
const testNameKey = '8f3da0c90ba2b89ff217da96f6088cbaf987a1b58bc33c3a5e526e53cec7cfed';
const testIdentifier = ':cic.area'
const testIdentifierKey = 'da6194e6f33726546e82c328df4c120b844d6427859156518bd600765bf8b2b7';

describe('custom', () => {

    context('with predefined data', () => {
        it('should create a custom object', () => {
            const custom = new Custom(testName, testObject);
            setTimeout(() => {
                assert.strictEqual(custom.name, testName);
                assert.deepStrictEqual(custom.m.data, testObject);
                assert.strictEqual(custom.key(), testNameKey)
            }, 0);
        });
    });

    context('without predefined data', () => {
        it('should create a custom object', () => {
            const custom = new Custom(testName);
            setTimeout(() => {
                assert.strictEqual(custom.name, testName);
                assert.deepStrictEqual(custom.m.data, {});
                assert.strictEqual(custom.key(), testNameKey)
            }, 0);
        });
    });

    describe('#toKey()', () => {
        context('without a custom identifier', () => {
            it('should generate a key from the custom name', async () => {
                assert.strictEqual(await Custom.toKey(testName), testNameKey);
            });
        });

        context('with a custom identifier', () => {
            it('should generate a key from the custom name with a custom identifier', async () => {
                assert.strictEqual(await Custom.toKey(testName, testIdentifier), testIdentifierKey);
            });
        });
    });
});
