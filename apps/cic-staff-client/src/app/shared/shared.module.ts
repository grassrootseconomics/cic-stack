import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TopbarComponent } from '@app/shared/topbar/topbar.component';
import { FooterComponent } from '@app/shared/footer/footer.component';
import { SidebarComponent } from '@app/shared/sidebar/sidebar.component';
import { MenuSelectionDirective } from '@app/shared/_directives/menu-selection.directive';
import { MenuToggleDirective } from '@app/shared/_directives/menu-toggle.directive';
import { RouterModule } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { TokenRatioPipe } from '@app/shared/_pipes/token-ratio.pipe';
import { ErrorDialogComponent } from '@app/shared/error-dialog/error-dialog.component';
import { MatDialogModule } from '@angular/material/dialog';
import { SafePipe } from '@app/shared/_pipes/safe.pipe';
import { NetworkStatusComponent } from './network-status/network-status.component';
import { UnixDatePipe } from './_pipes/unix-date.pipe';
import { SignatureUserPipe } from './_pipes/signature-user.pipe';

@NgModule({
  declarations: [
    TopbarComponent,
    FooterComponent,
    SidebarComponent,
    MenuSelectionDirective,
    MenuToggleDirective,
    TokenRatioPipe,
    ErrorDialogComponent,
    SafePipe,
    NetworkStatusComponent,
    UnixDatePipe,
    SignatureUserPipe,
  ],
  exports: [
    TopbarComponent,
    FooterComponent,
    SidebarComponent,
    MenuSelectionDirective,
    TokenRatioPipe,
    SafePipe,
    NetworkStatusComponent,
    UnixDatePipe,
    SignatureUserPipe,
  ],
  imports: [CommonModule, RouterModule, MatIconModule, MatDialogModule],
})
export class SharedModule {}
