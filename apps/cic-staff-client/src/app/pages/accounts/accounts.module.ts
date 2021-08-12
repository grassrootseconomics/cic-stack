import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { AccountsRoutingModule } from '@pages/accounts/accounts-routing.module';
import { AccountsComponent } from '@pages/accounts/accounts.component';
import { SharedModule } from '@app/shared/shared.module';
import { AccountDetailsComponent } from '@pages/accounts/account-details/account-details.component';
import { CreateAccountComponent } from '@pages/accounts/create-account/create-account.component';
import { MatTableModule } from '@angular/material/table';
import { MatSortModule } from '@angular/material/sort';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatPaginatorModule } from '@angular/material/paginator';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { TransactionsModule } from '@pages/transactions/transactions.module';
import { MatTabsModule } from '@angular/material/tabs';
import { MatRippleModule } from '@angular/material/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ReactiveFormsModule } from '@angular/forms';
import { AccountSearchComponent } from './account-search/account-search.component';
import { MatSnackBarModule } from '@angular/material/snack-bar';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { AccountHistoryComponent } from './account-history/account-history.component';

@NgModule({
  declarations: [
    AccountsComponent,
    AccountDetailsComponent,
    CreateAccountComponent,
    AccountSearchComponent,
    AccountHistoryComponent,
  ],
  exports: [AccountHistoryComponent],
  imports: [
    CommonModule,
    AccountsRoutingModule,
    SharedModule,
    MatTableModule,
    MatSortModule,
    MatCheckboxModule,
    MatPaginatorModule,
    MatInputModule,
    MatFormFieldModule,
    MatButtonModule,
    MatCardModule,
    MatIconModule,
    MatSelectModule,
    TransactionsModule,
    MatTabsModule,
    MatRippleModule,
    MatProgressSpinnerModule,
    ReactiveFormsModule,
    MatSnackBarModule,
    MatProgressBarModule,
  ],
})
export class AccountsModule {}
