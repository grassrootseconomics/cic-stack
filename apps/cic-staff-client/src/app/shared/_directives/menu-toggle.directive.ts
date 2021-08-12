// Core imports
import { Directive, ElementRef, Renderer2 } from '@angular/core';

/** Toggle availability of sidebar on menu toggle click. */
@Directive({
  selector: '[appMenuToggle]',
})
export class MenuToggleDirective {
  /**
   * Handle click events on the html element.
   *
   * @param elementRef - A wrapper around a native element inside of a View.
   * @param renderer - Extend this base class to implement custom rendering.
   */
  constructor(private elementRef: ElementRef, private renderer: Renderer2) {
    this.renderer.listen(this.elementRef.nativeElement, 'click', () => {
      this.onMenuToggle();
    });
  }

  /** Toggle the availability of the sidebar. */
  onMenuToggle(): void {
    const sidebar: HTMLElement = document.getElementById('sidebar');
    sidebar?.classList.toggle('active');
    const content: HTMLElement = document.getElementById('content');
    content?.classList.toggle('active');
    const sidebarCollapse: HTMLElement = document.getElementById('sidebarCollapse');
    sidebarCollapse?.classList.toggle('active');
  }
}
