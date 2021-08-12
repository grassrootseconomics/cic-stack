// Core imports
import { ElementRef, Renderer2 } from '@angular/core';

// Application imports
import { MenuSelectionDirective } from '@app/shared/_directives/menu-selection.directive';

describe('MenuSelectionDirective', () => {
  // tslint:disable-next-line:prefer-const
  let elementRef: ElementRef;
  // tslint:disable-next-line:prefer-const
  let renderer: Renderer2;

  beforeEach(() => {
    // renderer = new
  });

  it('should create an instance', () => {
    const directive = new MenuSelectionDirective(elementRef, renderer);
    expect(directive).toBeTruthy();
  });
});
