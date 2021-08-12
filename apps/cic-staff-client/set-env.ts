const { writeFile } = require('fs');
const { argv } = require('yargs');
const colors = require('colors');
require('dotenv').config();

const environment = argv.environment;
const isProduction = environment === 'prod';

const targetPath = isProduction ? `./src/environments/environment.prod.ts` : `./src/environments/environment.dev.ts`;

const environmentVars = `import {NgxLoggerLevel} from 'ngx-logger';

export const environment = {
  production: ${isProduction},
  bloxbergChainId: ${process.env.CIC_CHAIN_ID || 8996},
  logLevel: ${process.env.LOG_LEVEL || 'NgxLoggerLevel.ERROR'},
  serverLogLevel: ${process.env.SERVER_LOG_LEVEL || 'NgxLoggerLevel.OFF'},
  loggingUrl: '${process.env.CIC_LOGGING_URL || ''}',
  cicMetaUrl: '${process.env.CIC_META_URL || 'https://meta.dev.grassrootseconomics.net'}',
  publicKeysUrl: '${process.env.CIC_KEYS_URL || 'https://dev.grassrootseconomics.net/.well-known/publickeys'}',
  cicCacheUrl: '${process.env.CIC_CACHE_URL || 'https://cache.dev.grassrootseconomics.net'}',
  web3Provider: '${process.env.CIC_WEB3_PROVIDER || 'wss://bloxberg-ws.dev.grassrootseconomics.net'}',
  cicUssdUrl: '${process.env.CIC_USSD_URL || 'https://ussd.dev.grassrootseconomics.net'}',
  registryAddress: '${process.env.CIC_REGISTRY_ADDRESS || '0xea6225212005e86a4490018ded4bf37f3e772161'}',
  trustedDeclaratorAddress: '${process.env.CIC_TRUSTED_ADDRESS || '0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C'}'
};
`;

function setConfigs(configs): void {
  writeFile(targetPath, configs, err => {
    if (err) {
      throw console.error(err);
    } else {
      console.log(colors.green(`Wrote variables to '${targetPath}`));
    }
  });
}


if (isProduction) {
  console.log(colors.cyan('Running in production environment!'));
  setConfigs(environmentVars);
} else {
  console.log(colors.cyan('Running in development environment!'));
  setConfigs(environmentVars);
}

