// Core imports
import {
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
  HttpResponse,
} from '@angular/common/http';
import { Injectable } from '@angular/core';

// Third party imports
import { Observable } from 'rxjs';
import { finalize, tap } from 'rxjs/operators';

// Application imports
import { LoggingService } from '@app/_services/logging.service';

/** Intercepts and handles of events from outgoing HTTP request. */
@Injectable()
export class LoggingInterceptor implements HttpInterceptor {
  /**
   * Initialization of the logging interceptor.
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
    return next.handle(request);
    // this.loggingService.sendInfoLevelMessage(request);
    // const startTime: number = Date.now();
    // let status: string;
    //
    // return next.handle(request).pipe(tap(event => {
    //   status = '';
    //   if (event instanceof HttpResponse) {
    //     status = 'succeeded';
    //   }
    // }, error => status = 'failed'),
    //   finalize(() => {
    //   const elapsedTime: number = Date.now() - startTime;
    //   const message: string = `${request.method} request for ${request.urlWithParams} ${status} in ${elapsedTime} ms`;
    //   this.loggingService.sendInfoLevelMessage(message);
    // }));
  }
}
