// Core imports
import { ElementRef, Renderer2 } from '@angular/core';

// Application imports
import { MenuToggleDirective } from '@app/shared/_directives/menu-toggle.directive';

describe('MenuToggleDirective', () => {
  // tslint:disable-next-line:prefer-const
  let elementRef: ElementRef;
  // tslint:disable-next-line:prefer-const
  let renderer: Renderer2;
  it('should create an instance', () => {
    const directive = new MenuToggleDirective(elementRef, renderer);
    expect(directive).toBeTruthy();
  });
});
