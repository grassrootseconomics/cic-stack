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
 * Role guard implementation.
 * Dictates access to routes depending on the user's role.
 */
@Injectable({
  providedIn: 'root',
})
export class RoleGuard implements CanActivate {
  /**
   * Instantiates the role guard class.
   *
   * @param router - A service that provides navigation among views and URL manipulation capabilities.
   */
  constructor(private router: Router) {}

  /**
   * Returns whether navigation to a specific route is acceptable.
   * Checks if the user has the required role to access the route.
   *
   * @param route - Contains the information about a route associated with a component loaded in an outlet at a particular moment in time.
   * ActivatedRouteSnapshot can also be used to traverse the router state tree.
   * @param state - Represents the state of the router at a moment in time.
   * @returns true - If the user's role matches with accepted roles.
   */
  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean | UrlTree> | Promise<boolean | UrlTree> | boolean | UrlTree {
    const currentUser = JSON.parse(localStorage.getItem(atob('CICADA_USER')));
    if (currentUser) {
      if (route.data.roles && route.data.roles.indexOf(currentUser.role) === -1) {
        this.router.navigate(['/']);
        return false;
      }
      return true;
    }

    this.router.navigate(['/auth'], { queryParams: { returnUrl: state.url } });
    return false;
  }
}
