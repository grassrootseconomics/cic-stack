// Third party imports
import { KeyStore } from 'cic-client-meta';
// TODO should we put this on the mutable key store object
import * as openpgp from 'openpgp';

/** An openpgp Keyring instance. */
const keyring = new openpgp.Keyring();

/**
 * Mutable Key store interface.
 *
 * @extends KeyStore
 */
interface MutableKeyStore extends KeyStore {
  /** Remove all keys from the keyring. */
  clearKeysInKeyring(): void;
  /**
   * Get all the encryption keys.
   * @returns An array of encryption keys.
   * @remarks
   * Current implementation doesn't include encryption keys.
   * This is included to appease the implemented Keystore interface.
   */
  getEncryptKeys(): Array<any>;
  /**
   * Get the first private key's fingerprint.
   * @returns The first private key's fingerprint.
   */
  getFingerprint(): string;
  /**
   * Get a key's keyId.
   * @param key - The key to fetch the keyId from.
   * @returns The key's keyId.
   */
  getKeyId(key: any): string;
  /**
   * Get keys from the keyring using their keyId.
   * @param keyId - The keyId of the keys to be fetched from the keyring.
   * @returns An array of the keys with that keyId.
   */
  getKeysForId(keyId: string): Array<any>;
  /**
   * Get the first private key.
   * @returns The first private key.
   */
  getPrivateKey(): any;
  /**
   * Get a private key from the keyring using it's keyId.
   * @param keyId - The keyId of the private key to be fetched from the keyring.
   * @returns The private key with that keyId.
   */
  getPrivateKeyForId(keyId: string): any;
  /**
   * Get the first private key's keyID.
   * @returns The first private key's keyId.
   */
  getPrivateKeyId(): string;
  /**
   * Get all private keys.
   * @returns An array of all private keys.
   */
  getPrivateKeys(): Array<any>;
  /**
   * Get a public key from the keyring using it's keyId.
   * @param keyId - The keyId of the public key to be fetched from the keyring.
   * @returns The public key with that keyId.
   */
  getPublicKeyForId(keyId: string): any;
  /**
   * Get a public key from the keyring using it's subkeyId.
   * @param subkeyId - The subkeyId of the public key to be fetched from the keyring.
   * @returns The public key with that subkeyId.
   */
  getPublicKeyForSubkeyId(subkeyId: string): any;
  /**
   * Get all the public keys.
   * @returns An array of public keys.
   */
  getPublicKeys(): Array<any>;
  /**
   * Get public keys from the keyring using their address.
   * @param address - The address of the public keys to be fetched from the keyring.
   * @returns An array of the public keys with that address.
   */
  getPublicKeysForAddress(address: string): Array<any>;
  /**
   * Get all the trusted active keys.
   * @returns An array of trusted active keys.
   */
  getTrustedActiveKeys(): Array<any>;
  /**
   * Get all the trusted keys.
   * @returns An array of trusted keys.
   */
  getTrustedKeys(): Array<any>;
  /**
   * Add a key pair to keyring.
   * @async
   * @param publicKey - The public key to be added to the keyring.
   * @param privateKey - The private key to be added to the keyring.
   * @throws Error
   */
  importKeyPair(publicKey: any, privateKey: any): Promise<void>;
  /**
   * Add private key to keyring.
   * @async
   * @param privateKey - The private key to be added to the keyring.
   * @throws Error
   */
  importPrivateKey(privateKey: any): Promise<void>;
  /**
   * Add public key to keyring.
   * @async
   * @param publicKey - The public key to be added to the keyring.
   * @throws Error
   */
  importPublicKey(publicKey: any): Promise<void>;
  /**
   * Verify that a private key is encrypted.
   * @async
   * @param privateKey - The private key to verify.
   * @returns true - If private key is encrypted.
   */
  isEncryptedPrivateKey(privateKey: any): Promise<boolean>;
  /**
   * Test if the input is a valid key.
   * @async
   * @param key - The input to be validated.
   * @returns true - If the input is a valid key.
   */
  isValidKey(key: any): Promise<boolean>;
  /**
   * Instantiate the keyring in the keystore.
   * @async
   */
  loadKeyring(): void;
  /**
   * Remove a public key from the keyring using it's keyId.
   * @param keyId - The keyId of the keys to be removed from the keyring.
   * @returns An array of the removed keys.
   */
  removeKeysForId(keyId: string): Array<any>;
  /**
   * Remove a public key from the keyring.
   * @param publicKey - The public key to be removed from the keyring.
   * @returns The removed public key.
   */
  removePublicKey(publicKey: any): any;
  /**
   * Remove a public key from the keyring using it's keyId.
   * @param keyId - The keyId of the public key to be removed from the keyring.
   * @returns The removed public key.
   */
  removePublicKeyForId(keyId: string): any;
  /**
   * Sign message using private key.
   * @async
   * @param plainText - The message to be signed.
   * @returns The generated signature.
   */
  sign(plainText: string): Promise<any>;
}

/** Provides a keyring for pgp keys. */
class MutablePgpKeyStore implements MutableKeyStore {
  /** Remove all keys from the keyring. */
  clearKeysInKeyring(): void {
    keyring.clear();
  }

  /**
   * Get all the encryption keys.
   * @returns An array of encryption keys.
   * @remarks
   * Current implementation doesn't include encryption keys.
   * This is included to appease the implemented Keystore interface.
   */
  getEncryptKeys(): Array<any> {
    return [];
  }

  /**
   * Get the first private key's fingerprint.
   * @returns The first private key's fingerprint.
   */
  getFingerprint(): string {
    // TODO Handle multiple keys
    return (
      keyring.privateKeys &&
      keyring.privateKeys.keys[0] &&
      keyring.privateKeys.keys[0].keyPacket &&
      keyring.privateKeys.keys[0].keyPacket.fingerprint
    );
  }

  /**
   * Get a key's keyId.
   * @param key - The key to fetch the keyId from.
   * @returns The key's keyId.
   */
  getKeyId(key: any): string {
    return key.getKeyId().toHex();
  }

  /**
   * Get keys from the keyring using their keyId.
   * @param keyId - The keyId of the keys to be fetched from the keyring.
   * @returns An array of the keys with that keyId.
   */
  getKeysForId(keyId: string): Array<any> {
    return keyring.getKeysForId(keyId);
  }

  /**
   * Get the first private key.
   * @returns The first private key.
   */
  getPrivateKey(): any {
    return keyring.privateKeys && keyring.privateKeys.keys[0];
  }

  /**
   * Get a private key from the keyring using it's keyId.
   * @param keyId - The keyId of the private key to be fetched from the keyring.
   * @returns The private key with that keyId.
   */
  getPrivateKeyForId(keyId): any {
    return keyring.privateKeys && keyring.privateKeys.getForId(keyId);
  }

  /**
   * Get the first private key's keyID.
   * @returns The first private key's keyId.
   */
  getPrivateKeyId(): string {
    // TODO is there a library that comes with angular for doing this?
    return (
      keyring.privateKeys &&
      keyring.privateKeys.keys[0] &&
      keyring.privateKeys.keys[0].getKeyId().toHex()
    );
  }

  /**
   * Get all private keys.
   * @returns An array of all private keys.
   */
  getPrivateKeys(): Array<any> {
    return keyring.privateKeys && keyring.privateKeys.keys;
  }

  /**
   * Get a public key from the keyring using it's keyId.
   * @param keyId - The keyId of the public key to be fetched from the keyring.
   * @returns The public key with that keyId.
   */
  getPublicKeyForId(keyId): any {
    return keyring.publicKeys && keyring.publicKeys.getForId(keyId);
  }

  /**
   * Get a public key from the keyring using it's subkeyId.
   * @param subkeyId - The subkeyId of the public key to be fetched from the keyring.
   * @returns The public key with that subkeyId.
   */
  getPublicKeyForSubkeyId(subkeyId): any {
    return keyring.publicKeys && keyring.publicKeys.getForId(subkeyId, true);
  }

  /**
   * Get all the public keys.
   * @returns An array of public keys.
   */
  getPublicKeys(): Array<any> {
    return keyring.publicKeys && keyring.publicKeys.keys;
  }

  /**
   * Get public keys from the keyring using their address.
   * @param address - The address of the public keys to be fetched from the keyring.
   * @returns An array of the public keys with that address.
   */
  getPublicKeysForAddress(address): Array<any> {
    return keyring.publicKeys && keyring.publicKeys.getForAddress(address);
  }

  /**
   * Get all the trusted active keys.
   * @returns An array of trusted active keys.
   */
  getTrustedActiveKeys(): Array<any> {
    return keyring.publicKeys && keyring.publicKeys.keys;
  }

  /**
   * Get all the trusted keys.
   * @returns An array of trusted keys.
   */
  getTrustedKeys(): Array<any> {
    return keyring.publicKeys && keyring.publicKeys.keys;
  }

  /**
   * Add a key pair to keyring.
   * @async
   * @param publicKey - The public key to be added to the keyring.
   * @param privateKey - The private key to be added to the keyring.
   * @throws Error
   */
  async importKeyPair(publicKey: any, privateKey: any): Promise<void> {
    try {
      await keyring.publicKeys.importKey(publicKey);
      await keyring.privateKeys.importKey(privateKey);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Add private key to keyring.
   * @async
   * @param privateKey - The private key to be added to the keyring.
   * @throws Error
   */
  async importPrivateKey(privateKey: any): Promise<void> {
    try {
      await keyring.privateKeys.importKey(privateKey);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Add public key to keyring.
   * @async
   * @param publicKey - The public key to be added to the keyring.
   * @throws Error
   */
  async importPublicKey(publicKey: any): Promise<void> {
    try {
      await keyring.publicKeys.importKey(publicKey);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Verify that a private key is encrypted.
   * @async
   * @param privateKey - The private key to verify.
   * @returns true - If private key is encrypted.
   */
  async isEncryptedPrivateKey(privateKey: any): Promise<boolean> {
    const imported = await openpgp.key.readArmored(privateKey);
    for (const key of imported.keys) {
      if (key.isDecrypted()) {
        return false;
      }
    }
    return true;
  }

  /**
   * Test if the input is a valid key.
   * @async
   * @param key - The input to be validated.
   * @returns true - If the input is a valid key.
   */
  async isValidKey(key): Promise<boolean> {
    // There is supposed to be an openpgp.readKey() method but I can't find it?
    const testKey = await openpgp.key.readArmored(key);
    return !testKey.err;
  }

  /**
   * Instantiate the keyring in the keystore.
   * @async
   */
  async loadKeyring(): Promise<void> {
    await keyring.load();
    await keyring.store();
  }

  /**
   * Remove a public key from the keyring using it's keyId.
   * @param keyId - The keyId of the keys to be removed from the keyring.
   * @returns An array of the removed keys.
   */
  removeKeysForId(keyId): Array<any> {
    return keyring.removeKeysForId(keyId);
  }

  /**
   * Remove a public key from the keyring.
   * @param publicKey - The public key to be removed from the keyring.
   * @returns The removed public key.
   */
  removePublicKey(publicKey: any): any {
    const keyId = publicKey.getKeyId().toHex();
    return keyring.publicKeys && keyring.publicKeys.removeForId(keyId);
  }

  /**
   * Remove a public key from the keyring using it's keyId.
   * @param keyId - The keyId of the public key to be removed from the keyring.
   * @returns The removed public key.
   */
  removePublicKeyForId(keyId): any {
    return keyring.publicKeys && keyring.publicKeys.removeForId(keyId);
  }

  /**
   * Sign message using private key.
   * @async
   * @param plainText - The message to be signed.
   * @returns The generated signature.
   */
  async sign(plainText): Promise<any> {
    const privateKey = this.getPrivateKey();
    if (!privateKey.isDecrypted()) {
      const password = window.prompt('password');
      await privateKey.decrypt(password);
    }
    const opts = {
      message: openpgp.message.fromText(plainText),
      privateKeys: [privateKey],
      detached: true,
    };
    const signatureObject = await openpgp.sign(opts);
    return signatureObject.signature;
  }
}

/** @exports */
export { MutableKeyStore, MutablePgpKeyStore };
