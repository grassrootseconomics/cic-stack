/**
 * Copies set text to clipboard.
 *
 * @example
 * copies 'Hello World!' to the clipboard and prints "true":
 * ```typescript
 * console.log(copyToClipboard('Hello World!'));
 * ```
 *
 * @param text - The text to be copied to the clipboard.
 * @returns true - If the copy operation is successful.
 */
function copyToClipboard(text: any): boolean {
  // create our hidden div element
  const hiddenCopy: HTMLDivElement = document.createElement('div');
  // set the innerHTML of the div
  hiddenCopy.innerHTML = text;
  // set the position to be absolute and off the screen
  hiddenCopy.classList.add('clipboard');

  // check and see if the user had a text selection range
  let currentRange: Range | boolean;
  if (document.getSelection().rangeCount > 0) {
    // the user has a text selection range, store it
    currentRange = document.getSelection().getRangeAt(0);
    // remove the current selection
    window.getSelection().removeRange(currentRange);
  } else {
    // they didn't have anything selected
    currentRange = false;
  }

  // append the div to the body
  document.body.appendChild(hiddenCopy);
  // create a selection range
  const copyRange: Range = document.createRange();
  // set the copy range to be the hidden div
  copyRange.selectNode(hiddenCopy);
  // add the copy range
  window.getSelection().addRange(copyRange);

  // since not all browsers support this, use a try block
  try {
    // copy the text
    document.execCommand('copy');
  } catch (err) {
    window.alert('Your Browser Does not support this! Error : ' + err);
    return false;
  }
  // remove the selection range (Chrome throws a warning if we don't.)
  window.getSelection().removeRange(copyRange);
  // remove the hidden div
  document.body.removeChild(hiddenCopy);

  // return the old selection range
  if (currentRange) {
    window.getSelection().addRange(currentRange);
  }

  return true;
}

/** @exports */
export { copyToClipboard };
