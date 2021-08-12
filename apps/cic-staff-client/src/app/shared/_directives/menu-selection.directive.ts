// Core imports
import { Directive, ElementRef, Renderer2 } from '@angular/core';

/** Toggle availability of sidebar on menu item selection. */
@Directive({
  selector: '[appMenuSelection]',
})
export class MenuSelectionDirective {
  /**
   * Handle click events on the html element.
   *
   * @param elementRef - A wrapper around a native element inside of a View.
   * @param renderer - Extend this base class to implement custom rendering.
   */
  constructor(private elementRef: ElementRef, private renderer: Renderer2) {
    this.renderer.listen(this.elementRef.nativeElement, 'click', () => {
      const mediaQuery = window.matchMedia('(max-width: 768px)');
      if (mediaQuery.matches) {
        this.onMenuSelect();
      }
    });
  }

  /** Toggle the availability of the sidebar. */
  onMenuSelect(): void {
    const sidebar: HTMLElement = document.getElementById('sidebar');
    if (!sidebar?.classList.contains('active')) {
      sidebar?.classList.add('active');
    }
    const content: HTMLElement = document.getElementById('content');
    if (!content?.classList.contains('active')) {
      content?.classList.add('active');
    }
    const sidebarCollapse: HTMLElement = document.getElementById('sidebarCollapse');
    if (sidebarCollapse?.classList.contains('active')) {
      sidebarCollapse?.classList.remove('active');
    }
  }
}
