function asciiToHex(str: string): string {
  const arr = [];
  for (let n = 0, l = str.length; n < l; n++) {
    arr.push(Number(str.charCodeAt(n)).toString(16));
  }
  return arr.join('');
}

export { asciiToHex };
