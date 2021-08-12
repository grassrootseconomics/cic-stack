import { Component, OnInit, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { checkOnlineStatus } from '@src/app/_helpers';

@Component({
  selector: 'app-network-status',
  templateUrl: './network-status.component.html',
  styleUrls: ['./network-status.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NetworkStatusComponent implements OnInit {
  online: boolean = navigator.onLine;

  constructor(private cdr: ChangeDetectorRef) {
    this.handleNetworkChange();
  }

  ngOnInit(): void {
    window.addEventListener('online', (event: any) => {
      this.online = true;
      this.cdr.detectChanges();
    });
    window.addEventListener('offline', (event: any) => {
      this.online = false;
      this.cdr.detectChanges();
    });
  }

  handleNetworkChange(): void {
    setTimeout(async () => {
      if (this.online !== (await checkOnlineStatus())) {
        this.online = await checkOnlineStatus();
        this.cdr.detectChanges();
      }
      this.handleNetworkChange();
    }, 3000);
  }
}
