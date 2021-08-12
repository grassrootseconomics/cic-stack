// Core imports
import { AbstractControl, ValidationErrors } from '@angular/forms';

/**
 * Provides methods to perform custom validation to form inputs.
 */
export class CustomValidator {
  /**
   * Sets errors to the confirm password input field if it does not match with the value in the password input field.
   *
   * @param control - The control object of the form being validated.
   */
  static passwordMatchValidator(control: AbstractControl): void {
    const password: string = control.get('password').value;
    const confirmPassword: string = control.get('confirmPassword').value;
    if (password !== confirmPassword) {
      control.get('confirmPassword').setErrors({ NoPasswordMatch: true });
    }
  }

  /**
   * Sets errors to a form field if it does not match with the regular expression given.
   *
   * @param regex - The regular expression to match with the form field.
   * @param error - Defines the map of errors to return from failed validation checks.
   * @returns The map of errors returned from failed validation checks.
   */
  static patternValidator(regex: RegExp, error: ValidationErrors): ValidationErrors | null {
    return (control: AbstractControl): { [key: string]: any } => {
      if (!control.value) {
        return null;
      }

      const valid: boolean = regex.test(control.value);
      return valid ? null : error;
    };
  }
}
