// Core imports
import { HttpEvent, HttpHandler, HttpInterceptor, HttpRequest } from '@angular/common/http';
import { Injectable } from '@angular/core';

// Third party imports
import { Observable } from 'rxjs';
import { environment } from '@src/environments/environment';

/** Intercepts and handles setting of configurations to outgoing HTTP request. */
@Injectable()
export class HttpConfigInterceptor implements HttpInterceptor {
  /** Initialization of http config interceptor. */
  constructor() {}

  /**
   * Intercepts HTTP requests.
   *
   * @param request - An outgoing HTTP request with an optional typed body.
   * @param next - The next HTTP handler or the outgoing request dispatcher.
   * @returns The forwarded request.
   */
  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    if (request.url.startsWith(environment.cicMetaUrl)) {
      const token: string = sessionStorage.getItem(btoa('CICADA_SESSION_TOKEN'));

      if (token) {
        request = request.clone({
          headers: request.headers.set('Authorization', 'Bearer ' + token),
        });
      }
    }

    return next.handle(request);
  }
}
