#!/usr/bin/env node
const colors = require('colors');
const {Meta} = require("../dist");

let { argv } = require('yargs')
    .usage('Usage: $0 -m http://localhost:63380 -n publickeys')
    .example(
        '$0 -m http://localhost:63380 -n publickeys',
        'Fetches the public keys blob from the meta server'
    )
    .option('m', {
        alias: 'metaurl',
        describe: 'The URL for the meta service',
        demandOption: 'The meta url is required',
        type: 'string',
        nargs: 1,
    })
    .option('n', {
        alias: 'name',
        describe: 'The name of the resource to be fetched from the meta service',
        demandOption: 'The name of the resource is required',
        type: 'string',
        nargs: 1,
    })
    .option('t', {
        alias: 'type',
        describe: 'The type of resource to be fetched from the meta service\n' +
            'Options: `user`, `phone` and `custom`\n' +
            'Defaults to `custom`',
        type: 'string',
        nargs: 1,
    })
    .epilog('Grassroots Economics (c) 2021')
    .wrap(null);

const metaUrl = argv.m;
const resourceName = argv.n;
let type = argv.t;
if (type === undefined) {
    type = 'custom'
}

(async () => {
    const identifier = await Meta.getIdentifier(resourceName, type);
    console.log(colors.cyan(`Meta server storage identifier: ${identifier}`));
    const metaResponse = await Meta.get(identifier, metaUrl);
    if (typeof metaResponse !== "object") {
        console.error(colors.red('Metadata get failed!'));
    }
    console.log(colors.green(metaResponse));
})();
