import * as assert from 'assert';
import {Phone} from "../src";

const testAddress = '0xc1912fee45d61c87cc5ea59dae31190fffff232d';
const testPhone = '+254123456789';
const testPhoneKey = 'be3cc8212b7eb57c6217ddd42230bd8ccd2f01382bf8c1c77d3a683fa5a9bb16';

describe('phone', () => {

    it('should create a phone object', () => {
        const phone = new Phone(testAddress, testPhone);
        setTimeout(() => {
            assert.strictEqual(phone.address, testAddress);
            assert.strictEqual(phone.m.data.msisdn, testPhone);
            assert.strictEqual(phone.key(), testPhoneKey)
        }, 0);
    });

    describe('#toKey()', () => {
        it('should generate a key from the phone number', async () => {
            assert.strictEqual(await Phone.toKey(testPhone), testPhoneKey);
        });
    });
});
