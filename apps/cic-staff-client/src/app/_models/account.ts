/** Account data interface */
interface AccountDetails {
  /** Age of user */
  age?: string;
  /** Token balance on account */
  balance?: number;
  /** Business category of user. */
  category?: string;
  /** Account registration day */
  date_registered: number;
  /** User's gender */
  gender: string;
  /** Account identifiers */
  identities: {
    evm: {
      'bloxberg:8996': string[];
      'oldchain:1': string[];
    };
    latitude: number;
    longitude: number;
  };
  /** User's location */
  location: {
    area?: string;
    area_name: string;
    area_type?: string;
  };
  /** Products or services provided by user. */
  products: string[];
  /** Type of account */
  type?: string;
  /** Personal identifying information of user */
  vcard: {
    email: [
      {
        value: string;
      }
    ];
    fn: [
      {
        value: string;
      }
    ];
    n: [
      {
        value: string[];
      }
    ];
    tel: [
      {
        meta: {
          TYP: string[];
        };
        value: string;
      }
    ];
    version: [
      {
        value: string;
      }
    ];
  };
}

/** Meta signature interface */
interface Signature {
  /** Algorithm used */
  algo: string;
  /** Data that was signed. */
  data: string;
  /** Message digest */
  digest: string;
  /** Encryption engine used. */
  engine: string;
}

/** Meta object interface */
interface Meta {
  /** Account details */
  data: AccountDetails;
  /** Meta store id */
  id: string;
  /** Signature used during write. */
  signature: Signature;
}

/** Meta response interface */
interface MetaResponse {
  /** Meta store id */
  id: string;
  /** Meta object */
  m: Meta;
}

/** Default account data object */
const defaultAccount: AccountDetails = {
  date_registered: Date.now(),
  gender: 'other',
  identities: {
    evm: {
      'bloxberg:8996': [''],
      'oldchain:1': [''],
    },
    latitude: 0,
    longitude: 0,
  },
  location: {
    area_name: 'Kilifi',
  },
  products: [],
  vcard: {
    email: [
      {
        value: '',
      },
    ],
    fn: [
      {
        value: 'Sarafu Contract',
      },
    ],
    n: [
      {
        value: ['Sarafu', 'Contract'],
      },
    ],
    tel: [
      {
        meta: {
          TYP: [],
        },
        value: '+254700000000',
      },
    ],
    version: [
      {
        value: '3.0',
      },
    ],
  },
};

/** @exports */
export { AccountDetails, Meta, MetaResponse, Signature, defaultAccount };
