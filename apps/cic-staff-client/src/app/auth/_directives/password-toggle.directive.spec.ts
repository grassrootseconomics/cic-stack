// Core imports
import { ElementRef, Renderer2 } from '@angular/core';

// Application imports
import { PasswordToggleDirective } from '@app/auth/_directives/password-toggle.directive';

// tslint:disable-next-line:prefer-const
let elementRef: ElementRef;
// tslint:disable-next-line:prefer-const
let renderer: Renderer2;

describe('PasswordToggleDirective', () => {
  it('should create an instance', () => {
    const directive = new PasswordToggleDirective(elementRef, renderer);
    expect(directive).toBeTruthy();
  });
});
