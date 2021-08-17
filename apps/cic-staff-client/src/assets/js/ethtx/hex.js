"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.add0x = exports.strip0x = exports.toHex = exports.fromHex = void 0;
// improve
function validHex(hexString) {
    return hexString;
}
function even(hexString) {
    if (hexString.length % 2 != 0) {
        hexString = '0' + hexString;
    }
    return hexString;
}
function strip0x(hexString) {
    if (hexString.length < 2) {
        throw new Error('invalid hex');
    }
    else if (hexString.substring(0, 2) == '0x') {
        hexString = hexString.substring(2);
    }
    return validHex(even(hexString));
}
exports.strip0x = strip0x;
function add0x(hexString) {
    if (hexString.length < 2) {
        throw new Error('invalid hex');
    }
    else if (hexString.substring(0, 2) != '0x') {
        hexString = '0x' + hexString;
    }
    return validHex(even(hexString));
}
exports.add0x = add0x;
function fromHex(hexString) {
    return new Uint8Array(hexString.match(/.{1,2}/g).map(function (byte) { return parseInt(byte, 16); }));
}
exports.fromHex = fromHex;
function toHex(bytes) {
    return bytes.reduce(function (str, byte) { return str + byte.toString(16).padStart(2, '0'); }, '');
}
exports.toHex = toHex;
