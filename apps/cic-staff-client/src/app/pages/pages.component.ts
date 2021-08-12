import { ChangeDetectionStrategy, Component } from '@angular/core';
import { environment } from '@src/environments/environment';

@Component({
  selector: 'app-pages',
  templateUrl: './pages.component.html',
  styleUrls: ['./pages.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PagesComponent {
  url: string = environment.dashboardUrl;

  constructor() {}
}
