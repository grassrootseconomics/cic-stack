/** Staff object interface */
interface Staff {
  /** Comment made on the public key. */
  comment: string;
  /** Email used to create the public key. */
  email: string;
  /** Name of the owner of the public key */
  name: string;
  /** Tags added to the public key. */
  tag: number;
  /** User ID of the owner of the public key. */
  userid: string;
}

/** @exports */
export { Staff };
