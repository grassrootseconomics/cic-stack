import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { PagesComponent } from './pages.component';

const routes: Routes = [
  { path: 'home', component: PagesComponent },
  {
    path: 'tx',
    loadChildren: () =>
      import('@pages/transactions/transactions.module').then((m) => m.TransactionsModule),
  },
  {
    path: 'settings',
    loadChildren: () => import('@pages/settings/settings.module').then((m) => m.SettingsModule),
  },
  {
    path: 'accounts',
    loadChildren: () => import('@pages/accounts/accounts.module').then((m) => m.AccountsModule),
  },
  {
    path: 'tokens',
    loadChildren: () => import('@pages/tokens/tokens.module').then((m) => m.TokensModule),
  },
  // {
  //   path: 'admin',
  //   loadChildren: () => import('@pages/admin/admin.module').then((m) => m.AdminModule),
  // },
  { path: '**', redirectTo: 'home', pathMatch: 'full' },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class PagesRoutingModule {}
