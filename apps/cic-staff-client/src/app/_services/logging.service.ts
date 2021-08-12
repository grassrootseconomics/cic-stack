import { Injectable, isDevMode } from '@angular/core';
import { NGXLogger } from 'ngx-logger';

@Injectable({
  providedIn: 'root',
})
export class LoggingService {
  constructor(private logger: NGXLogger) {
    // TRACE|DEBUG|INFO|LOG|WARN|ERROR|FATAL|OFF
    if (isDevMode()) {
      this.sendInfoLevelMessage('Dropping into debug mode');
    }
  }

  sendTraceLevelMessage(message: any, source: any, error: any): void {
    this.logger.trace(message, source, error);
  }

  sendDebugLevelMessage(message: any, source: any, error: any): void {
    this.logger.debug(message, source, error);
  }

  sendInfoLevelMessage(message: any): void {
    this.logger.info(message);
  }

  sendLogLevelMessage(message: any, source: any, error: any): void {
    this.logger.log(message, source, error);
  }

  sendWarnLevelMessage(message: any, error: any): void {
    this.logger.warn(message, error);
  }

  sendErrorLevelMessage(message: any, source: any, error: any): void {
    this.logger.error(message, source, error);
  }

  sendFatalLevelMessage(message: any, source: any, error: any): void {
    this.logger.fatal(message, source, error);
  }
}
