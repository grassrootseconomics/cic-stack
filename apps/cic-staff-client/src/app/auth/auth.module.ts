import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { AuthRoutingModule } from '@app/auth/auth-routing.module';
import { AuthComponent } from '@app/auth/auth.component';
import { ReactiveFormsModule } from '@angular/forms';
import { PasswordToggleDirective } from '@app/auth/_directives/password-toggle.directive';
import { MatCardModule } from '@angular/material/card';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatRippleModule } from '@angular/material/core';
import { SharedModule } from '@app/shared/shared.module';

@NgModule({
  declarations: [AuthComponent, PasswordToggleDirective],
  imports: [
    CommonModule,
    AuthRoutingModule,
    ReactiveFormsModule,
    MatCardModule,
    MatSelectModule,
    MatInputModule,
    MatButtonModule,
    MatRippleModule,
    SharedModule,
  ],
})
export class AuthModule {}
