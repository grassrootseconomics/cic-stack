import { Config } from 'kc-crdt-meta';
const fs = require('fs');

if (process.argv[2] === undefined) {
	process.stderr.write('Usage: node dumpConfig.js <configdir>\n');
	process.exit(1);
}
try {
	const stat = fs.statSync(process.argv[2]);
	if (!stat.isDirectory()) {
		throw 'not a directory';
	}
} catch {
	process.stderr.write('Not a directory: ' + process.argv[2] + '\n');
	process.exit(1);
}

const c = new Config(process.argv[2], process.env['CONFINI_ENV_PREFIX']);
c.process();
process.stdout.write(c.toString());
