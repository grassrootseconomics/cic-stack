import { ChangeDetectionStrategy, Component, HostListener, OnInit } from '@angular/core';
import {
  AuthService,
  BlockSyncService,
  ErrorDialogService,
  LoggingService,
  TokenService,
  TransactionService,
  UserService,
} from '@app/_services';
import { SwUpdate } from '@angular/service-worker';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs/operators';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnInit {
  title = 'CICADA';
  mediaQuery: MediaQueryList = window.matchMedia('(max-width: 768px)');
  url: string;
  accountDetailsRegex = '/accounts/[a-z,A-Z,0-9]{40}';

  constructor(
    private authService: AuthService,
    private blockSyncService: BlockSyncService,
    private errorDialogService: ErrorDialogService,
    private loggingService: LoggingService,
    private tokenService: TokenService,
    private transactionService: TransactionService,
    private userService: UserService,
    private swUpdate: SwUpdate,
    private router: Router
  ) {
    this.mediaQuery.addEventListener('change', this.onResize);
    this.onResize(this.mediaQuery);
  }

  async ngOnInit(): Promise<void> {
    await this.authService.init();
    await this.tokenService.init();
    await this.userService.init();
    await this.transactionService.init();
    try {
      const publicKeys = await this.authService.getPublicKeys();
      await this.authService.mutableKeyStore.importPublicKey(publicKeys);
      this.authService.getTrustedUsers();
    } catch (error) {
      this.errorDialogService.openDialog({
        message: 'Trusted keys endpoint cannot be reached. Please try again later.',
      });
      // TODO do something to halt user progress...show a sad cicada page 🦗?
    }
    if (!this.swUpdate.isEnabled) {
      this.swUpdate.available.subscribe(() => {
        if (confirm('New Version available. Load New Version?')) {
          window.location.reload();
        }
      });
    }
    await this.routeManagement();
  }

  // Load resize
  onResize(e): void {
    const sidebar: HTMLElement = document.getElementById('sidebar');
    const content: HTMLElement = document.getElementById('content');
    const sidebarCollapse: HTMLElement = document.getElementById('sidebarCollapse');
    if (sidebarCollapse?.classList.contains('active')) {
      sidebarCollapse?.classList.remove('active');
    }
    if (e.matches) {
      if (!sidebar?.classList.contains('active')) {
        sidebar?.classList.add('active');
      }
      if (!content?.classList.contains('active')) {
        content?.classList.add('active');
      }
    } else {
      if (sidebar?.classList.contains('active')) {
        sidebar?.classList.remove('active');
      }
      if (content?.classList.contains('active')) {
        content?.classList.remove('active');
      }
    }
  }

  @HostListener('window:cic_transfer', ['$event'])
  async cicTransfer(event: CustomEvent): Promise<void> {
    const transaction: any = event.detail.tx;
    await this.transactionService.setTransaction(transaction, 100);
  }

  @HostListener('window:cic_convert', ['$event'])
  async cicConvert(event: CustomEvent): Promise<void> {
    const conversion: any = event.detail.tx;
    await this.transactionService.setConversion(conversion, 100);
  }

  async routeManagement(): Promise<void> {
    await this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd))
      .forEach(async (routeInfo) => {
        if (routeInfo instanceof NavigationEnd) {
          this.url = routeInfo.url;
          if (!this.url.match(this.accountDetailsRegex) || !this.url.includes('tx')) {
            await this.blockSyncService.blockSync();
          }
          if (!this.url.includes('accounts')) {
            try {
              await this.userService.loadAccounts(100);
            } catch (error) {
              this.loggingService.sendErrorLevelMessage('Failed to load accounts', this, { error });
            }
          }
          if (!this.url.includes('tokens')) {
            this.tokenService.load.subscribe(async (status: boolean) => {
              if (status) {
                await this.tokenService.getTokens();
              }
            });
          }
        }
      });
  }
}
