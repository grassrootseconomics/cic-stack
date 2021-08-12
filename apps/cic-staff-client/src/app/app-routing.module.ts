import { NgModule } from '@angular/core';
import { Routes, RouterModule, PreloadAllModules } from '@angular/router';
import { AuthGuard } from '@app/_guards';

const routes: Routes = [
  { path: 'auth', loadChildren: () => import('@app/auth/auth.module').then((m) => m.AuthModule) },
  {
    path: '',
    loadChildren: () => import('@pages/pages.module').then((m) => m.PagesModule),
    canActivate: [AuthGuard],
  },
  { path: '**', redirectTo: '', pathMatch: 'full' },
];

@NgModule({
  imports: [
    RouterModule.forRoot(routes, {
      preloadingStrategy: PreloadAllModules,
      useHash: true,
    }),
  ],
  exports: [RouterModule],
})
export class AppRoutingModule {}
