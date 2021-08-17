declare function toValue(n: number): bigint;
declare function stringToValue(s: string): bigint;
declare function hexToValue(hx: string): bigint;
declare class Tx {
    nonce: number;
    gasPrice: number;
    gasLimit: number;
    to: Uint8Array;
    value: bigint;
    data: Uint8Array;
    v: number;
    r: Uint8Array;
    s: Uint8Array;
    chainId: number;
    _signatureSet: boolean;
    _workBuffer: ArrayBuffer;
    _outBuffer: DataView;
    _outBufferCursor: number;
    constructor(chainId: number);
    private serializeNumber;
    private write;
    serializeBytes(): Uint8Array;
    canonicalOrder(): Uint8Array[];
    serializeRLP(): Uint8Array;
    message(): Uint8Array;
    setSignature(r: Uint8Array, s: Uint8Array, v: number): void;
    clearSignature(): void;
}
export { Tx, stringToValue, hexToValue, toValue, };
