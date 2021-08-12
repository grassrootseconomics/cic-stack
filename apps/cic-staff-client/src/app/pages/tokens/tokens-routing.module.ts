import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { TokensComponent } from '@pages/tokens/tokens.component';
import { TokenDetailsComponent } from '@pages/tokens/token-details/token-details.component';

const routes: Routes = [
  { path: '', component: TokensComponent },
  { path: ':id', component: TokenDetailsComponent },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class TokensRoutingModule {}
