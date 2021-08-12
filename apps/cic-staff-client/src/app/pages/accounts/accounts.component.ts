import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  OnInit,
  ViewChild,
} from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { LoggingService, TokenService, UserService } from '@app/_services';
import { Router } from '@angular/router';
import { exportCsv } from '@app/_helpers';
import { strip0x } from '@src/assets/js/ethtx/dist/hex';
import { first } from 'rxjs/operators';
import { environment } from '@src/environments/environment';
import { AccountDetails } from '@app/_models';

@Component({
  selector: 'app-accounts',
  templateUrl: './accounts.component.html',
  styleUrls: ['./accounts.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccountsComponent implements OnInit, AfterViewInit {
  dataSource: MatTableDataSource<any>;
  accounts: Array<AccountDetails> = [];
  displayedColumns: Array<string> = ['name', 'phone', 'created', 'balance', 'location'];
  defaultPageSize: number = 10;
  pageSizeOptions: Array<number> = [10, 20, 50, 100];
  accountsType: string = 'all';
  accountTypes: Array<string>;
  tokenSymbol: string;
  loading: boolean = true;

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  constructor(
    private loggingService: LoggingService,
    private userService: UserService,
    private router: Router,
    private tokenService: TokenService
  ) {}

  async ngOnInit(): Promise<void> {
    this.userService.accountsSubject.subscribe((accounts) => {
      this.dataSource = new MatTableDataSource<any>(accounts);
      this.dataSource.paginator = this.paginator;
      this.dataSource.sort = this.sort;
      this.accounts = accounts;
      if (accounts.length > 0) {
        this.loading = false;
      }
    });
    try {
      await this.userService.loadAccounts(100);
    } catch (error) {
      this.loggingService.sendErrorLevelMessage('Failed to load accounts', this, { error });
    }
    this.userService
      .getAccountTypes()
      .pipe(first())
      .subscribe((res) => (this.accountTypes = res));
    this.tokenService.load.subscribe(async (status: boolean) => {
      if (status) {
        this.tokenSymbol = await this.tokenService.getTokenSymbol();
      }
    });
  }

  ngAfterViewInit(): void {
    if (this.dataSource) {
      this.dataSource.paginator = this.paginator;
      this.dataSource.sort = this.sort;
    }
  }

  doFilter(value: string): void {
    this.dataSource.filter = value.trim().toLocaleLowerCase();
  }

  async viewAccount(account): Promise<void> {
    await this.router.navigateByUrl(
      `/accounts/${strip0x(account.identities.evm[`bloxberg:${environment.bloxbergChainId}`][0])}`
    );
  }

  filterAccounts(): void {
    if (this.accountsType === 'all') {
      this.userService.accountsSubject.subscribe((accounts) => {
        this.dataSource.data = accounts;
        this.accounts = accounts;
      });
    } else {
      this.dataSource.data = this.accounts.filter((account) => account.type === this.accountsType);
    }
  }

  refreshPaginator(): void {
    if (!this.dataSource.paginator) {
      this.dataSource.paginator = this.paginator;
    }

    this.paginator._changePageSize(this.paginator.pageSize);
  }

  downloadCsv(): void {
    exportCsv(this.accounts, 'accounts');
  }
}
