/** Token object interface */
interface Token {
  /** Address of the deployed token contract. */
  address: string;
  /** Number of decimals to convert to smallest denomination of the token. */
  decimals: string;
  /** Name of the token. */
  name: string;
  /** Address of account that deployed token. */
  owner?: string;
  /** Token reserve to token minting ratio. */
  reserveRatio?: string;
  /** Token reserve information */
  reserves?: {
    '0xa686005CE37Dce7738436256982C3903f2E4ea8E'?: {
      weight: string;
      balance: string;
    };
  };
  /** Total token supply. */
  supply: string;
  /** The unique token symbol. */
  symbol: string;
}

/** @exports */
export { Token };
