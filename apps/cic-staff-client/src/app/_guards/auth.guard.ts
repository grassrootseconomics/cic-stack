// Core imports
import { Injectable } from '@angular/core';
import {
  ActivatedRouteSnapshot,
  CanActivate,
  Router,
  RouterStateSnapshot,
  UrlTree,
} from '@angular/router';

// Third party imports
import { Observable } from 'rxjs';

/**
 * Auth guard implementation.
 * Dictates access to routes depending on the authentication status.
 */
@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate {
  /**
   * Instantiates the auth guard class.
   *
   * @param router - A service that provides navigation among views and URL manipulation capabilities.
   */
  constructor(private router: Router) {}

  /**
   * Returns whether navigation to a specific route is acceptable.
   * Checks if the user has uploaded a private key.
   *
   * @param route - Contains the information about a route associated with a component loaded in an outlet at a particular moment in time.
   * ActivatedRouteSnapshot can also be used to traverse the router state tree.
   * @param state - Represents the state of the router at a moment in time.
   * @returns true - If there is an active private key in the user's localStorage.
   */
  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    if (sessionStorage.getItem(btoa('CICADA_SESSION_TOKEN'))) {
      return true;
    }
    this.router.navigate(['/auth']);
    return false;
  }
}
