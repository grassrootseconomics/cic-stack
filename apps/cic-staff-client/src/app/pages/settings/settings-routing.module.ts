import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';

import { SettingsComponent } from '@pages/settings/settings.component';
import { OrganizationComponent } from '@pages/settings/organization/organization.component';

const routes: Routes = [
  { path: '', component: SettingsComponent },
  { path: 'organization', component: OrganizationComponent },
  { path: '**', redirectTo: '', pathMatch: 'full' },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class SettingsRoutingModule {}
