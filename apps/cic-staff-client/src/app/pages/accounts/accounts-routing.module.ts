import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { AccountsComponent } from '@pages/accounts/accounts.component';
import { CreateAccountComponent } from '@pages/accounts/create-account/create-account.component';
import { AccountDetailsComponent } from '@pages/accounts/account-details/account-details.component';
import { AccountSearchComponent } from '@pages/accounts/account-search/account-search.component';

const routes: Routes = [
  { path: '', component: AccountsComponent },
  { path: 'search', component: AccountSearchComponent },
  // { path: 'create', component: CreateAccountComponent },
  { path: ':id', component: AccountDetailsComponent },
  { path: '**', redirectTo: '', pathMatch: 'full' },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class AccountsRoutingModule {}
