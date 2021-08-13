import { NgxLoggerLevel } from 'ngx-logger';

export const environment = {
  production: false,
  bloxbergChainId: 8996,
  logLevel: NgxLoggerLevel.ERROR,
  serverLogLevel: NgxLoggerLevel.OFF,
  loggingUrl: 'http://localhost:8000',
  cicMetaUrl: 'https://meta-auth.dev.grassrootseconomics.net',
  publicKeysUrl: 'https://dev.grassrootseconomics.net/.well-known/publickeys/',
  cicCacheUrl: 'https://cache.dev.grassrootseconomics.net',
  web3Provider: 'wss://bloxberg-ws.dev.grassrootseconomics.net',
  cicUssdUrl: 'https://user.dev.grassrootseconomics.net',
  registryAddress: '0xea6225212005e86a4490018ded4bf37f3e772161',
  trustedDeclaratorAddress: '0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C',
  dashboardUrl: 'https://dashboard.sarafu.network/',
};
