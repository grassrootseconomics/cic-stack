/** Action object interface */
interface Action {
  /** Action performed */
  action: string;
  /** Action approval status. */
  approval: boolean;
  /** Action ID */
  id: number;
  /** Admin's role in the system */
  role: string;
  /** Admin who initialized the action. */
  user: string;
}

/** @exports */
export { Action };
