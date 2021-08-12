/**
 * Returns the sum of all values in an array.
 *
 * @example
 * Prints 6 for the array [1, 2, 3]:
 * ```typescript
 * console.log(arraySum([1, 2, 3]));
 * ```
 *
 * @param arr - An array of numbers.
 * @return The sum of all values in the array.
 */
function arraySum(arr: Array<number>): number {
  return arr.reduce((accumulator, current) => accumulator + current, 0);
}

/** @exports */
export { arraySum };
