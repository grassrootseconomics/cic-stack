import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  OnInit,
  ViewChild,
} from '@angular/core';
import { BlockSyncService, TokenService, TransactionService, UserService } from '@app/_services';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { exportCsv } from '@app/_helpers';
import { first } from 'rxjs/operators';
import { Transaction } from '@app/_models';

@Component({
  selector: 'app-transactions',
  templateUrl: './transactions.component.html',
  styleUrls: ['./transactions.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TransactionsComponent implements OnInit, AfterViewInit {
  transactionDataSource: MatTableDataSource<any>;
  transactionDisplayedColumns: Array<string> = ['sender', 'recipient', 'value', 'created', 'type'];
  defaultPageSize: number = 10;
  pageSizeOptions: Array<number> = [10, 20, 50, 100];
  transactions: Array<Transaction>;
  transaction: Transaction;
  transactionsType: string = 'all';
  transactionsTypes: Array<string>;
  tokenSymbol: string;
  loading: boolean = true;

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  constructor(
    private blockSyncService: BlockSyncService,
    private transactionService: TransactionService,
    private userService: UserService,
    private tokenService: TokenService
  ) {}

  async ngOnInit(): Promise<void> {
    await this.blockSyncService.blockSync();
    this.transactionService.transactionsSubject.subscribe((transactions) => {
      this.transactionDataSource = new MatTableDataSource<any>(transactions);
      this.transactionDataSource.paginator = this.paginator;
      this.transactionDataSource.sort = this.sort;
      this.transactions = transactions;
      if (transactions.length > 0) {
        this.loading = false;
      }
    });
    this.userService
      .getTransactionTypes()
      .pipe(first())
      .subscribe((res) => (this.transactionsTypes = res));
    this.tokenService.load.subscribe(async (status: boolean) => {
      if (status) {
        this.tokenSymbol = await this.tokenService.getTokenSymbol();
      }
    });
  }

  viewTransaction(transaction): void {
    this.transaction = transaction;
  }

  doFilter(value: string, dataSource): void {
    dataSource.filter = value.trim().toLocaleLowerCase();
  }

  filterTransactions(): void {
    if (this.transactionsType === 'all') {
      this.transactionService.transactionsSubject.subscribe((transactions) => {
        this.transactionDataSource.data = transactions;
        this.transactions = transactions;
      });
    } else {
      this.transactionDataSource.data = this.transactions.filter(
        (transaction) => transaction.type + 's' === this.transactionsType
      );
    }
  }

  ngAfterViewInit(): void {
    if (this.transactionDataSource) {
      this.transactionDataSource.paginator = this.paginator;
      this.transactionDataSource.sort = this.sort;
    }
  }

  downloadCsv(): void {
    exportCsv(this.transactions, 'transactions');
  }
}
