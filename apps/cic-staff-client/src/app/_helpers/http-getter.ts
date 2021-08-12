import { rejectBody } from '@app/_helpers/global-error-handler';

/** Provides an avenue of fetching resources via HTTP calls. */
function HttpGetter(): void {}

/**
 * Fetches files using HTTP get requests.
 *
 * @param filename -  The filename to fetch.
 * @returns The HTTP response text.
 */
HttpGetter.prototype.get = (filename) =>
  new Promise((resolve, reject) => {
    fetch(filename).then((response) => {
      if (response.ok) {
        resolve(response.text());
      } else {
        reject(rejectBody(response));
      }
      return;
    });
  });

/** @exports */
export { HttpGetter };
