import * as assert from 'assert';

import { User } from "../src";

const testAddress = '0xc1912fee45d61c87cc5ea59dae31190fffff232d';
const testAddressKey = 'a51472cb4df63b199a4de01335b1b4d1bbee27ff4f03340aa1d592f26c6acfe2';
const testUser = {
    user: {
        firstName: 'Test',
        lastName: 'User'
    }
}

describe('user', () => {

    context('without predefined data', () => {
        it('should create a user object', () => {
            const user = new User(testAddress);
            setTimeout(() => {
                assert.strictEqual(user.address, testAddress);
                assert.strictEqual(user.key(), testAddressKey);
                assert.strictEqual(user.m.data.user.firstName, '');
                assert.strictEqual(user.m.data.user.lastName, '');
            }, 0);
        });
    });

    context('with predefined data', () => {
        it('should create a user object', () => {
            const user = new User(testAddress, testUser);
            setTimeout(() => {
                assert.strictEqual(user.address, testAddress);
                assert.strictEqual(user.key(), testAddressKey);
                assert.strictEqual(user.m.data.user.firstName, testUser.user.firstName);
                assert.strictEqual(user.m.data.user.lastName, testUser.user.lastName);
            }, 0);
        });
    });

    describe('#setName()', () => {
        it('should set user\'s names to metadata', () => {
            const user = new User(testAddress);
            user.setName(testUser.user.firstName, testUser.user.lastName);
            assert.strictEqual(user.m.data.user.firstName, testUser.user.firstName);
            assert.strictEqual(user.m.data.user.lastName, testUser.user.lastName);
        });
    });

    describe('#toKey()', () => {
        it('should generate a key from the user\'s address', async () => {
            assert.strictEqual(await User.toKey(testAddress), testAddressKey);
        });
    });
});
