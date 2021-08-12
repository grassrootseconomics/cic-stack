// Third party imports
import * as openpgp from 'openpgp';

// Application imports
import { MutableKeyStore } from '@app/_pgp/pgp-key-store';
import { LoggingService } from '@app/_services/logging.service';

/** Signable object interface */
interface Signable {
  /** The message to be signed. */
  digest(): string;
}

/** Signature object interface */
interface Signature {
  /** Encryption algorithm used */
  algo: string;
  /** Data to be signed. */
  data: string;
  /** Message digest */
  digest: string;
  /** Encryption engine used. */
  engine: string;
}

/** Signer interface */
interface Signer {
  /**
   * Get the private key fingerprint.
   * @returns A private key fingerprint.
   */
  fingerprint(): string;
  /** Event triggered on successful signing of message. */
  onsign(signature: Signature): void;
  /** Event triggered on successful verification of a signature. */
  onverify(flag: boolean): void;
  /**
   * Load the message digest.
   * @param material - A signable object.
   * @returns true - If digest has been loaded successfully.
   */
  prepare(material: Signable): boolean;
  /**
   * Signs a message using a private key.
   * @async
   * @param digest - The message to be signed.
   */
  sign(digest: string): Promise<void>;
  /**
   * Verify that signature is valid.
   * @param digest - The message that was signed.
   * @param signature - The generated signature.
   */
  verify(digest: string, signature: Signature): void;
}

/** Provides functionality for signing and verifying signed messages. */
class PGPSigner implements Signer {
  /** Encryption algorithm used */
  algo = 'sha256';
  /** Message digest */
  dgst: string;
  /** Encryption engine used. */
  engine = 'pgp';
  /** A keystore holding pgp keys. */
  keyStore: MutableKeyStore;
  /** A service that provides logging capabilities. */
  loggingService: LoggingService;
  /** Event triggered on successful signing of message. */
  onsign: (signature: Signature) => void;
  /** Event triggered on successful verification of a signature. */
  onverify: (flag: boolean) => void;
  /** Generated signature */
  signature: Signature;

  /**
   * Initializing the Signer.
   * @param keyStore - A keystore holding pgp keys.
   */
  constructor(keyStore: MutableKeyStore) {
    this.keyStore = keyStore;
    this.onsign = (signature: Signature) => {};
    this.onverify = (flag: boolean) => {};
  }

  /**
   * Get the private key fingerprint.
   * @returns A private key fingerprint.
   */
  public fingerprint(): string {
    return this.keyStore.getFingerprint();
  }

  /**
   * Load the message digest.
   * @param material - A signable object.
   * @returns true - If digest has been loaded successfully.
   */
  public prepare(material: Signable): boolean {
    this.dgst = material.digest();
    return true;
  }

  /**
   * Signs a message using a private key.
   * @async
   * @param digest - The message to be signed.
   */
  public async sign(digest: string): Promise<void> {
    const m = openpgp.cleartext.fromText(digest);
    const pk = this.keyStore.getPrivateKey();
    if (!pk.isDecrypted()) {
      const password = window.prompt('password');
      await pk.decrypt(password);
    }
    const opts = {
      message: m,
      privateKeys: [pk],
      detached: true,
    };
    openpgp
      .sign(opts)
      .then((s) => {
        this.signature = {
          engine: this.engine,
          algo: this.algo,
          data: s.signature,
          // TODO: fix for browser later
          digest,
        };
        this.onsign(this.signature);
      })
      .catch((e) => {
        this.loggingService.sendErrorLevelMessage(e.message, this, { error: e });
        this.onsign(undefined);
      });
  }

  /**
   * Verify that signature is valid.
   * @param digest - The message that was signed.
   * @param signature - The generated signature.
   */
  public verify(digest: string, signature: Signature): void {
    openpgp.signature
      .readArmored(signature.data)
      .then((sig) => {
        const opts = {
          message: openpgp.cleartext.fromText(digest),
          publicKeys: this.keyStore.getTrustedKeys(),
          signature: sig,
        };
        openpgp.verify(opts).then((v) => {
          let i = 0;
          for (i = 0; i < v.signatures.length; i++) {
            const s = v.signatures[i];
            if (s.valid) {
              this.onverify(s);
              return;
            }
          }
          this.loggingService.sendErrorLevelMessage(
            `Checked ${i} signature(s) but none valid`,
            this,
            { error: '404 Not found!' }
          );
          this.onverify(false);
        });
      })
      .catch((e) => {
        this.loggingService.sendErrorLevelMessage(e.message, this, { error: e });
        this.onverify(false);
      });
  }
}

/** @exports */
export { PGPSigner, Signable, Signature, Signer };
