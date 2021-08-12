// Core imports
import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Injectable } from '@angular/core';

// Third party imports
import { Observable } from 'rxjs';

// Application imports
import { LoggingService } from '@app/_services/logging.service';
import { checkOnlineStatus } from '@app/_helpers';

/** Intercepts and handles of events from outgoing HTTP request. */
@Injectable()
export class ConnectionInterceptor implements HttpInterceptor {
  /**
   * Initialization of the connection interceptor.
   *
   * @param loggingService - A service that provides logging capabilities.
   */
  constructor(private loggingService: LoggingService) {}

  /**
   * Intercepts HTTP requests.
   *
   * @param request - An outgoing HTTP request with an optional typed body.
   * @param next - The next HTTP handler or the outgoing request dispatcher.
   * @returns The forwarded request.
   */
  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    checkOnlineStatus().then((online) => {
      if (!online) {
        this.loggingService.sendErrorLevelMessage('No internet connection on device!', this, {
          error: `NetworkError when attempting to fetch resource ${request.url}.`,
        });
        return;
      } else {
        return next.handle(request);
      }
    });
    return next.handle(request);
  }
}
