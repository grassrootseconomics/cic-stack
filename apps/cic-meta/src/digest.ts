import * as crypto from './crypto';

interface Addressable {
	key(): string
	digest(): string
}

function stringToBytes(s:string) {
	const a = new Uint8Array(20);
	let j = 2;
	for (let i = 0; i < a.byteLength; i++) {
		const n = parseInt(s.substring(j, j+2), 16);
		a[i] = n;
		j += 2;
	}
	return a;
}

function bytesToHex(a:Uint8Array) {
	let s = '';
	for (let i = 0; i < a.byteLength; i++) {
		const h = '00' + a[i].toString(16);
		s += h.slice(-2);
	}
	return s;
}

async function mergeKey(a:Uint8Array, s:Uint8Array) {
	const y = new Uint8Array(a.byteLength + s.byteLength);
	for (let i = 0; i < a.byteLength; i++) {
		y[i] = a[i];
	}
	for (let i = 0; i < s.byteLength; i++) {
		y[a.byteLength + i] = s[i];
	}
	const z = await crypto.subtle.digest('SHA-256', y);
	return bytesToHex(new Uint8Array(z));
}

async function toKey(v:string, salt:string) {
	const a = stringToBytes(v);
	const s = new TextEncoder().encode(salt);
	return await mergeKey(a, s);
}


async function toAddressKey(zeroExHex:string, salt:string) {
	const a = addressToBytes(zeroExHex);
	const s = new TextEncoder().encode(salt);
	return await mergeKey(a, s);
}

const re_addrHex = /^0[xX][a-fA-F0-9]{40}$/;
function addressToBytes(s:string) {
	if (!s.match(re_addrHex)) {
		throw 'invalid address hex';
	}
	return stringToBytes(s);
}

export {
	toKey,
	toAddressKey,
	mergeKey,
	bytesToHex,
	addressToBytes,
	Addressable,
}
