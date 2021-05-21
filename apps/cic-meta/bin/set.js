#!/usr/bin/env node
const fs = require("fs");
const colors = require('colors');
const {Meta} = require("../dist");

let { argv } = require('yargs')
    .usage('Usage: $0 -m http://localhost:63380 -k ./privatekeys.asc -n publickeys -r ./publickeys.asc')
    .example(
        '$0 -m http://localhost:63380 -k ./privatekeys.asc -n publickeys -r ./publickeys.asc',
        'Updates the public keys blob to the meta server'
    )
    .option('m', {
        alias: 'metaurl',
        describe: 'The URL for the meta service',
        demandOption: 'The meta url is required',
        type: 'string',
        nargs: 1,
    })
    .option('k', {
        alias: 'privatekey',
        describe: 'The PGP private key blob file used to sign the changes to the meta service',
        demandOption: 'The private key file is required',
        type: 'string',
        nargs: 1,
    })
    .option('n', {
        alias: 'name',
        describe: 'The name of the resource to be set or updated to the meta service',
        demandOption: 'The name of the resource is required',
        type: 'string',
        nargs: 1,
    })
    .option('r', {
        alias: 'resource',
        describe: 'The resource file to be set or updated to the meta service',
        demandOption: 'The resource file is required',
        type: 'string',
        nargs: 1,
    })
    .option('t', {
        alias: 'type',
        describe: 'The type of resource to be set or updated to the meta service\n' +
            'Options: `user`, `phone` and `custom`\n' +
            'Defaults to `custom`',
        type: 'string',
        nargs: 1,
    })
    .epilog('Grassroots Economics (c) 2021')
    .wrap(null);

const metaUrl = argv.m;
const privateKeyFile = argv.k;
const resourceName = argv.n;
const resourceFile = argv.r;
let type = argv.t;
if (type === undefined) {
    type = 'custom'
}

const privateKey = readFile(privateKeyFile);
const resource = readFile(resourceFile);

(async () => {
    if (privateKey && resource) {
        const identifier = await Meta.getIdentifier(resourceName, type);
        console.log(colors.cyan(`Meta server storage identifier: ${identifier}`));
        const meta = new Meta(metaUrl, privateKey);
        meta.onload = async (status) => {
            const response = await meta.set(identifier, resource)
            console.log(colors.green(response));
        }
    }
})();

function readFile(filename) {
    if(!fs.existsSync(filename)) {
        console.log(colors.red(`File ${filename} not found`));
        return;
    }
    return fs.readFileSync(filename, {encoding: 'utf8', flag: 'r'});
}
