// Core imports
import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest,
} from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';

// Third party imports
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

// Application imports
import { ErrorDialogService, LoggingService } from '@app/_services';

/** Intercepts and handles errors from outgoing HTTP request. */
@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  /**
   * Initialization of the error interceptor.
   *
   * @param errorDialogService - A service that provides a dialog box for displaying errors to the user.
   * @param loggingService - A service that provides logging capabilities.
   * @param router - A service that provides navigation among views and URL manipulation capabilities.
   */
  constructor(
    private errorDialogService: ErrorDialogService,
    private loggingService: LoggingService,
    private router: Router
  ) {}

  /**
   * Intercepts HTTP requests.
   *
   * @param request - An outgoing HTTP request with an optional typed body.
   * @param next - The next HTTP handler or the outgoing request dispatcher.
   * @returns The error caught from the request.
   */
  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    return next.handle(request).pipe(
      catchError((err: HttpErrorResponse) => {
        let errorMessage: string;
        if (err.error instanceof ErrorEvent) {
          // A client-side or network error occurred. Handle it accordingly.
          errorMessage = `An error occurred: ${err.error.message}`;
        } else {
          // The backend returned an unsuccessful response code.
          // The response body may contain clues as to what went wrong.
          errorMessage = `Backend returned code ${err.status}, body was: ${JSON.stringify(
            err.error
          )}`;
        }
        this.loggingService.sendErrorLevelMessage(errorMessage, this, { error: err });
        switch (err.status) {
          case 401: // unauthorized
            this.router.navigateByUrl('/auth').then();
            break;
          case 403: // forbidden
            this.errorDialogService.openDialog({
              message: 'Access to resource is not allowed (Error 403)',
            });
            // alert('Access to resource is not allowed!');
            break;
        }
        // Return an observable with a user-facing error message.
        return throwError(err);
      })
    );
  }
}
