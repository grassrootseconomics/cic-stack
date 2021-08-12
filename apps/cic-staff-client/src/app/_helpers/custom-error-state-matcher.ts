// Core imports
import { ErrorStateMatcher } from '@angular/material/core';
import { FormControl, FormGroupDirective, NgForm } from '@angular/forms';

/**
 * Custom provider that defines how form controls behave with regards to displaying error messages.
 *
 */
export class CustomErrorStateMatcher implements ErrorStateMatcher {
  /**
   * Checks whether an invalid input has been made and an error should be made.
   *
   * @param control - Tracks the value and validation status of an individual form control.
   * @param form - Binding of an existing FormGroup to a DOM element.
   * @returns true - If an invalid input has been made to the form control.
   */
  isErrorState(control: FormControl | null, form: FormGroupDirective | NgForm | null): boolean {
    const isSubmitted: boolean = form && form.submitted;
    return !!(control && control.invalid && (control.dirty || control.touched || isSubmitted));
  }
}
