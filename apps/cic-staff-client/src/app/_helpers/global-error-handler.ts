// Core imports
import { HttpErrorResponse } from '@angular/common/http';
import { ErrorHandler, Injectable } from '@angular/core';
import { Router } from '@angular/router';

// Application imports
import { LoggingService } from '@app/_services/logging.service';

/**
 * A generalized http response error.
 *
 * @extends Error
 */
export class HttpError extends Error {
  /** The error's status code. */
  public status: number;

  /**
   * Initialize the HttpError class.
   *
   * @param message - The message given by the error.
   * @param status - The status code given by the error.
   */
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'HttpError';
  }
}

/**
 * Provides a hook for centralized exception handling.
 *
 * @extends ErrorHandler
 */
@Injectable()
export class GlobalErrorHandler extends ErrorHandler {
  /**
   * An array of sentence sections that denote warnings.
   */
  private sentencesForWarningLogging: Array<string> = [];

  /**
   * Initialization of the Global Error Handler.
   *
   * @param loggingService - A service that provides logging capabilities.
   * @param router - A service that provides navigation among views and URL manipulation capabilities.
   */
  constructor(private loggingService: LoggingService, private router: Router) {
    super();
  }

  /**
   * Handles different types of errors.
   *
   * @param error - An error objects thrown when a runtime errors occurs.
   */
  handleError(error: Error): void {
    this.logError(error);
    const message: string = error.message ? error.message : error.toString();

    // if (error.status) {
    //   error = new Error(message);
    // }

    const errorTraceString: string = `Error message:\n${message}.\nStack trace: ${error.stack}`;

    const isWarning: boolean = this.isWarning(errorTraceString);
    if (isWarning) {
      this.loggingService.sendWarnLevelMessage(errorTraceString, { error });
    } else {
      this.loggingService.sendErrorLevelMessage(errorTraceString, this, { error });
    }

    throw error;
  }

  /**
   * Checks if an error is of type warning.
   *
   * @param errorTraceString - A description of the error and it's stack trace.
   * @returns true - If the error is of type warning.
   */
  private isWarning(errorTraceString: string): boolean {
    let isWarning: boolean = true;
    if (errorTraceString.includes('/src/app/')) {
      isWarning = false;
    }

    this.sentencesForWarningLogging.forEach((whiteListSentence: string) => {
      if (errorTraceString.includes(whiteListSentence)) {
        isWarning = true;
      }
    });

    return isWarning;
  }

  /**
   * Write appropriate logs according to the type of error.
   *
   * @param error - An error objects thrown when a runtime errors occurs.
   */
  logError(error: any): void {
    const route: string = this.router.url;
    if (error instanceof HttpErrorResponse) {
      this.loggingService.sendErrorLevelMessage(
        `There was an HTTP error on route ${route}.\n${error.message}.\nStatus code: ${
          (error as HttpErrorResponse).status
        }`,
        this,
        { error }
      );
    } else if (error instanceof TypeError) {
      this.loggingService.sendErrorLevelMessage(
        `There was a Type error on route ${route}.\n${error.message}`,
        this,
        { error }
      );
    } else if (error instanceof Error) {
      this.loggingService.sendErrorLevelMessage(
        `There was a general error on route ${route}.\n${error.message}`,
        this,
        { error }
      );
    } else {
      this.loggingService.sendErrorLevelMessage(
        `Nobody threw an error but something happened on route ${route}!`,
        this,
        { error }
      );
    }
  }
}

export function rejectBody(error): { status: any; statusText: any } {
  return {
    status: error.status,
    statusText: error.statusText,
  };
}
