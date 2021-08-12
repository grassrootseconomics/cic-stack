/** Settings class */
class Settings {
  /** CIC Registry instance */
  registry: any;
  /** A resource for searching through blocks on the blockchain network. */
  scanFilter: any;
  /** Transaction Helper instance */
  txHelper: any;
  /** Web3 Object */
  w3: W3 = {
    engine: undefined,
    provider: undefined,
  };

  /**
   * Initialize the settings.
   *
   * @param scanFilter - A resource for searching through blocks on the blockchain network.
   */
  constructor(scanFilter: any) {
    this.scanFilter = scanFilter;
  }
}

/** Web3 object interface */
interface W3 {
  /** An active web3 instance connected to the blockchain network. */
  engine: any;
  /** The connection socket to the blockchain network. */
  provider: any;
}

/** @exports */
export { Settings, W3 };
