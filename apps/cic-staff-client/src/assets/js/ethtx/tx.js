"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.toValue = exports.hexToValue = exports.stringToValue = exports.Tx = void 0;
var hex_1 = require("./hex");
var sha3_1 = require("sha3");
var RLP = require('rlp');
function isAddress(a) {
    return a !== undefined && a.length == 20;
}
function toValue(n) {
    return BigInt(n);
}
exports.toValue = toValue;
function stringToValue(s) {
    return BigInt(s);
}
exports.stringToValue = stringToValue;
function hexToValue(hx) {
    return BigInt(hex_1.add0x(hx));
}
exports.hexToValue = hexToValue;
var Tx = /** @class */ (function () {
    function Tx(chainId) {
        this.chainId = chainId;
        this.nonce = 0;
        this.gasPrice = 0;
        this.gasLimit = 0;
        this.to = new Uint8Array(32);
        this.data = new Uint8Array(0);
        this.value = BigInt(0);
        this._workBuffer = new ArrayBuffer(32);
        this._outBuffer = new DataView(new ArrayBuffer(1024 * 1024));
        this._outBufferCursor = 0;
        this.clearSignature();
    }
    Tx.prototype.serializeNumber = function (n) {
        var view = new DataView(this._workBuffer);
        view.setBigUint64(0, BigInt(0));
        view.setBigUint64(0, n);
        var zeroOffset = 0;
        for (zeroOffset = 0; zeroOffset < 8; zeroOffset++) {
            if (view.getInt8(zeroOffset) > 0) {
                break;
            }
        }
        return new Uint8Array(this._workBuffer).slice(zeroOffset, 8);
    };
    Tx.prototype.write = function (data) {
        var _this = this;
        data.forEach(function (v) {
            _this._outBuffer.setInt8(_this._outBufferCursor, v);
            _this._outBufferCursor++;
        });
    };
    Tx.prototype.serializeBytes = function () {
        if (!isAddress(this.to)) {
            throw new Error('invalid address');
        }
        var nonce = this.serializeNumber(BigInt(this.nonce));
        this.write(nonce);
        var gasPrice = this.serializeNumber(BigInt(this.gasPrice));
        this.write(gasPrice);
        var gasLimit = this.serializeNumber(BigInt(this.gasLimit));
        this.write(gasLimit);
        this.write(this.to);
        var value = this.serializeNumber(this.value);
        this.write(value);
        this.write(this.data);
        var v = this.serializeNumber(BigInt(this.v));
        this.write(v);
        this.write(this.r);
        this.write(this.s);
        return new Uint8Array(this._outBuffer.buffer).slice(0, this._outBufferCursor);
    };
    Tx.prototype.canonicalOrder = function () {
        return [
            this.serializeNumber(BigInt(this.nonce)),
            this.serializeNumber(BigInt(this.gasPrice)),
            this.serializeNumber(BigInt(this.gasLimit)),
            this.to,
            this.serializeNumber(this.value),
            this.data,
            this.serializeNumber(BigInt(this.v)),
            this.r,
            this.s,
        ];
    };
    Tx.prototype.serializeRLP = function () {
        return RLP.encode(this.canonicalOrder());
    };
    Tx.prototype.message = function () {
        // TODO: Can we do without Buffer, pleeease?
        var h = new sha3_1.Keccak(256);
        var b = new Buffer(this.serializeRLP());
        h.update(b);
        return h.digest();
    };
    Tx.prototype.setSignature = function (r, s, v) {
        if (this._signatureSet) {
            throw new Error('Signature already set');
        }
        if (r.length != 32 || s.length != 32) {
            throw new Error('Invalid signature length');
        }
        if (v < 0 || v > 3) {
            throw new Error('Invalid recid');
        }
        this.r = r;
        this.s = s;
        this.v = (this.chainId * 2) + 35 + v;
        this._signatureSet = true;
    };
    Tx.prototype.clearSignature = function () {
        this.r = new Uint8Array(0);
        this.s = new Uint8Array(0);
        this.v = this.chainId;
        this._signatureSet = false;
    };
    return Tx;
}());
exports.Tx = Tx;
