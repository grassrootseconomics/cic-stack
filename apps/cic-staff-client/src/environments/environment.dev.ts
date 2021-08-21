import { NgxLoggerLevel } from 'ngx-logger';

export const environment = {
  production: false,
  bloxbergChainId: 8996,
  logLevel: NgxLoggerLevel.DEBUG,
  serverLogLevel: NgxLoggerLevel.OFF,
  loggingUrl: '',
  cicMetaUrl: 'http://meta.localhost',
  publicKeysUrl: 'https://dev.grassrootseconomics.net/.well-known/publickeys/',
  cicCacheUrl: 'http://cache.localhost',
  web3Provider: 'http://bloxberg.localhost',
  cicUssdUrl: 'http://user.localhost',
  registryAddress: '0xea6225212005e86a4490018ded4bf37f3e772161',
  trustedDeclaratorAddress: '0xEb3907eCad74a0013c259D5874AE7f22DcBcC95C',
  dashboardUrl: 'https://dashboard.sarafu.network/',
};
