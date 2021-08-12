// Core imports
import { Directive, ElementRef, Input, Renderer2 } from '@angular/core';

/** Toggle password form field input visibility */
@Directive({
  selector: '[appPasswordToggle]',
})
export class PasswordToggleDirective {
  /** The password form field id */
  @Input()
  id: string;

  /** The password form field icon id */
  @Input()
  iconId: string;

  /**
   * Handle click events on the html element.
   *
   * @param elementRef - A wrapper around a native element inside of a View.
   * @param renderer - Extend this base class to implement custom rendering.
   */
  constructor(private elementRef: ElementRef, private renderer: Renderer2) {
    this.renderer.listen(this.elementRef.nativeElement, 'click', () => {
      this.togglePasswordVisibility();
    });
  }

  /** Toggle the visibility of the password input field value and accompanying icon. */
  togglePasswordVisibility(): void {
    const password: HTMLElement = document.getElementById(this.id);
    const icon: HTMLElement = document.getElementById(this.iconId);
    // @ts-ignore
    if (password.type === 'password') {
      // @ts-ignore
      password.type = 'text';
      icon.classList.remove('fa-eye');
      icon.classList.add('fa-eye-slash');
    } else {
      // @ts-ignore
      password.type = 'password';
      icon.classList.remove('fa-eye-slash');
      icon.classList.add('fa-eye');
    }
  }
}
