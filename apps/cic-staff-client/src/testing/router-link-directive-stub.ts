import { Directive, HostListener, Input } from '@angular/core';

@Directive({
  selector: '[appRouterLink]',
})
// tslint:disable-next-line:directive-class-suffix
export class RouterLinkDirectiveStub {
  // tslint:disable-next-line:no-input-rename
  @Input('routerLink') linkParams: any;
  navigatedTo: any = null;

  @HostListener('click')
  onClick(): void {
    this.navigatedTo = this.linkParams;
  }
}
