declare function strip0x(hexString: string): string;
declare function add0x(hexString: string): string;
declare function fromHex(hexString: string): Uint8Array;
declare function toHex(bytes: Uint8Array): string;
export { fromHex, toHex, strip0x, add0x, };
