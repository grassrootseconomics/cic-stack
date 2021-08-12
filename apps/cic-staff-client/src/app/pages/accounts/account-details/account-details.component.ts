import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  OnInit,
  ViewChild,
} from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import {
  BlockSyncService,
  LocationService,
  LoggingService,
  TokenService,
  TransactionService,
  UserService,
} from '@app/_services';
import { ActivatedRoute, Params, Router } from '@angular/router';
import { first } from 'rxjs/operators';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { copyToClipboard, CustomErrorStateMatcher, exportCsv } from '@app/_helpers';
import { MatSnackBar } from '@angular/material/snack-bar';
import { add0x, strip0x } from '@src/assets/js/ethtx/dist/hex';
import { environment } from '@src/environments/environment';
import { AccountDetails, Transaction } from '@app/_models';

@Component({
  selector: 'app-account-details',
  templateUrl: './account-details.component.html',
  styleUrls: ['./account-details.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccountDetailsComponent implements OnInit, AfterViewInit {
  transactionsDataSource: MatTableDataSource<any>;
  transactionsDisplayedColumns: Array<string> = ['sender', 'recipient', 'value', 'created', 'type'];
  transactionsDefaultPageSize: number = 10;
  transactionsPageSizeOptions: Array<number> = [10, 20, 50, 100];
  @ViewChild('TransactionTablePaginator', { static: true }) transactionTablePaginator: MatPaginator;
  @ViewChild('TransactionTableSort', { static: true }) transactionTableSort: MatSort;

  userDataSource: MatTableDataSource<any>;
  userDisplayedColumns: Array<string> = ['name', 'phone', 'created', 'balance', 'location'];
  usersDefaultPageSize: number = 10;
  usersPageSizeOptions: Array<number> = [10, 20, 50, 100];
  @ViewChild('UserTablePaginator', { static: true }) userTablePaginator: MatPaginator;
  @ViewChild('UserTableSort', { static: true }) userTableSort: MatSort;

  historyDataSource: MatTableDataSource<any>;
  historyDisplayedColumns: Array<string> = [
    'actor',
    'signer',
    'message',
    'sequence',
    'dependencies',
    'timestamp',
  ];
  historyDefaultPageSize: number = 10;
  historyPageSizeOptions: Array<number> = [10, 20, 50, 100];
  @ViewChild('HistoryTablePaginator', { static: true }) historyTablePaginator: MatPaginator;
  @ViewChild('HistoryTableSort', { static: true }) historyTableSort: MatSort;

  accountInfoForm: FormGroup;
  account: AccountDetails;
  accountAddress: string;
  accountStatus: any;
  accounts: Array<AccountDetails> = [];
  accountsType: string = 'all';
  categories: Array<string>;
  areaNames: Array<string>;
  areaTypes: Array<string>;
  transaction: any;
  transactions: Array<Transaction>;
  transactionsType: string = 'all';
  accountTypes: Array<string>;
  transactionsTypes: Array<string>;
  genders: Array<string>;
  matcher: CustomErrorStateMatcher = new CustomErrorStateMatcher();
  submitted: boolean = false;
  bloxbergLink: string;
  tokenSymbol: string;
  category: string;
  area: string;
  areaType: string;
  accountsLoading: boolean = true;
  transactionsLoading: boolean = true;
  histories: Array<any> = [];
  history: any;
  historyLoading: boolean = true;

  constructor(
    private formBuilder: FormBuilder,
    private locationService: LocationService,
    private transactionService: TransactionService,
    private userService: UserService,
    private route: ActivatedRoute,
    private router: Router,
    private tokenService: TokenService,
    private loggingService: LoggingService,
    private blockSyncService: BlockSyncService,
    private cdr: ChangeDetectorRef,
    private snackBar: MatSnackBar
  ) {
    this.route.paramMap.subscribe((params: Params) => {
      this.accountAddress = add0x(params.get('id'));
      this.bloxbergLink =
        'https://blockexplorer.bloxberg.org/address/' + this.accountAddress + '/transactions';
    });
  }

  async ngOnInit(): Promise<void> {
    this.buildAccountsInfoForm();
    this.transactionService.resetTransactionsList();
    await this.blockSyncService.blockSync(this.accountAddress);
    this.userService.resetAccountsList();
    (await this.userService.getAccountByAddress(this.accountAddress, 100, true)).subscribe(
      async (res) => {
        if (res !== undefined) {
          this.account = res;
          this.cdr.detectChanges();
          this.queryLocationAndCategory(this.account);
          this.populateAccountsInfoForm(this.account);
          this.userService
            .getAccountStatus(this.account.vcard?.tel[0].value)
            .pipe(first())
            .subscribe((response) => (this.accountStatus = response.status));
        } else {
          alert('Account not found!');
        }
      }
    );
    this.populateDataTables();
    this.loadSearchData();
    this.tokenService.load.subscribe(async (status: boolean) => {
      if (status) {
        this.tokenSymbol = await this.tokenService.getTokenSymbol();
      }
    });
  }

  ngAfterViewInit(): void {
    if (this.userDataSource) {
      this.userDataSource.paginator = this.userTablePaginator;
      this.userDataSource.sort = this.userTableSort;
    }
    if (this.transactionsDataSource) {
      this.transactionsDataSource.paginator = this.transactionTablePaginator;
      this.transactionsDataSource.sort = this.transactionTableSort;
    }
    if (this.historyDataSource) {
      this.historyDataSource.paginator = this.historyTablePaginator;
      this.historyDataSource.sort = this.historyTableSort;
    }
  }

  doTransactionFilter(value: string): void {
    this.transactionsDataSource.filter = value.trim().toLocaleLowerCase();
  }

  doUserFilter(value: string): void {
    this.userDataSource.filter = value.trim().toLocaleLowerCase();
  }

  viewTransaction(transaction): void {
    this.transaction = transaction;
  }

  viewHistory(history): void {
    this.history = history;
  }

  viewAccount(account): void {
    this.router.navigateByUrl(
      `/accounts/${strip0x(account.identities.evm[`bloxberg:${environment.bloxbergChainId}`][0])}`
    );
  }

  get accountInfoFormStub(): any {
    return this.accountInfoForm.controls;
  }

  async saveInfo(): Promise<void> {
    this.submitted = true;
    if (this.accountInfoForm.invalid || !confirm(`Change user's profile information?`)) {
      return;
    }
    const accountKey = await this.userService.changeAccountInfo(
      this.accountAddress,
      this.accountInfoFormStub.firstName.value + ', ' + this.accountInfoFormStub.lastName.value,
      this.accountInfoFormStub.phoneNumber.value,
      this.accountInfoFormStub.age.value,
      this.accountInfoFormStub.type.value,
      this.accountInfoFormStub.bio.value,
      this.accountInfoFormStub.gender.value,
      this.accountInfoFormStub.businessCategory.value,
      this.accountInfoFormStub.userLocation.value,
      this.accountInfoFormStub.location.value,
      this.accountInfoFormStub.locationType.value,
      this.account.vcard?.tel[0].value
    );
    this.submitted = false;
  }

  filterAccounts(): void {
    if (this.accountsType === 'all') {
      this.userService.accountsSubject.subscribe((accounts) => {
        this.userDataSource.data = accounts;
        this.accounts = accounts;
      });
    } else {
      this.userDataSource.data = this.accounts.filter(
        (account) => account.type === this.accountsType
      );
    }
  }

  filterTransactions(): void {
    if (this.transactionsType === 'all') {
      this.transactionService.transactionsSubject.subscribe((transactions) => {
        this.transactionsDataSource.data = transactions;
        this.transactions = transactions;
      });
    } else {
      this.transactionsDataSource.data = this.transactions.filter(
        (transaction) => transaction.type + 's' === this.transactionsType
      );
    }
  }

  resetPin(): void {
    if (!confirm(`Reset user's pin?`)) {
      return;
    }
    this.userService
      .resetPin(this.account.vcard.tel[0].value)
      .pipe(first())
      .subscribe((res) => {
        this.loggingService.sendInfoLevelMessage(`Response: ${res}`);
      });
  }

  downloadCsv(data: any, filename: string): void {
    exportCsv(data, filename);
  }

  copyAddress(): void {
    if (copyToClipboard(this.accountAddress)) {
      this.snackBar.open(this.accountAddress + ' copied successfully!', 'Close', {
        duration: 3000,
      });
    }
  }

  getKeyValue(obj: any): string {
    let str = '';
    if (obj instanceof Object) {
      for (const [key, value] of Object.entries(obj)) {
        str += `${key}: ${value} `;
      }
    }
    return str;
  }

  buildAccountsInfoForm(): void {
    this.accountInfoForm = this.formBuilder.group({
      firstName: ['', Validators.required],
      lastName: ['', Validators.required],
      phoneNumber: ['', Validators.required],
      age: [''],
      type: ['', Validators.required],
      bio: ['', Validators.required],
      gender: ['', Validators.required],
      businessCategory: ['', Validators.required],
      userLocation: ['', Validators.required],
      location: ['', Validators.required],
      locationType: ['', Validators.required],
    });
  }

  populateAccountsInfoForm(accountInfo: AccountDetails): void {
    const fullName = accountInfo.vcard?.fn[0].value.split(' ');
    this.accountInfoForm.patchValue({
      firstName: fullName[0].split(',')[0],
      lastName: fullName.slice(1).join(' '),
      phoneNumber: accountInfo.vcard?.tel[0].value,
      age: accountInfo.age,
      type: accountInfo.type,
      bio: accountInfo.products,
      gender: accountInfo.gender,
      businessCategory: accountInfo.category || this.category || 'other',
      userLocation: accountInfo.location.area_name,
      location: accountInfo.location.area || this.area || 'other',
      locationType: accountInfo.location.area_type || this.areaType || 'other',
    });
  }

  populateDataTables(): void {
    this.userService.accountsSubject.subscribe((accounts) => {
      this.userDataSource = new MatTableDataSource<any>(accounts);
      this.userDataSource.paginator = this.userTablePaginator;
      this.userDataSource.sort = this.userTableSort;
      this.accounts = accounts;
      if (accounts.length > 0) {
        this.accountsLoading = false;
      }
      this.cdr.detectChanges();
    });

    this.transactionService.transactionsSubject.subscribe((transactions) => {
      this.transactionsDataSource = new MatTableDataSource<any>(transactions);
      this.transactionsDataSource.paginator = this.transactionTablePaginator;
      this.transactionsDataSource.sort = this.transactionTableSort;
      this.transactions = transactions;
      if (transactions.length > 0) {
        this.transactionsLoading = false;
      }
      this.cdr.detectChanges();
    });

    this.userService.historySubject.subscribe(async (histories) => {
      this.historyDataSource = new MatTableDataSource<any>(histories);
      this.historyDataSource.paginator = this.historyTablePaginator;
      this.historyDataSource.sort = this.historyTableSort;
      this.histories = histories;
      if (histories.length > 0) {
        this.historyLoading = false;
      }
      this.cdr.detectChanges();
    });
  }

  queryLocationAndCategory(accountInfo: AccountDetails): void {
    this.locationService.areaNamesSubject.subscribe((response) => {
      this.area = this.locationService.getAreaNameByLocation(
        accountInfo.location.area_name,
        response
      );
      this.cdr.detectChanges();
      this.locationService.areaTypesSubject.subscribe((result) => {
        this.areaType = this.locationService.getAreaTypeByArea(this.area, result);
        this.cdr.detectChanges();
      });
    });
    this.userService.categoriesSubject.subscribe((result) => {
      this.category = this.userService.getCategoryByProduct(accountInfo.products[0], result);
      this.cdr.detectChanges();
    });
  }

  loadSearchData(): void {
    this.userService.getCategories();
    this.userService.categoriesSubject.subscribe((res) => {
      this.categories = Object.keys(res);
    });
    this.locationService.getAreaNames();
    this.locationService.areaNamesSubject.subscribe((res) => {
      this.areaNames = Object.keys(res);
    });
    this.locationService.getAreaTypes();
    this.locationService.areaTypesSubject.subscribe((res) => {
      this.areaTypes = Object.keys(res);
    });
    this.userService
      .getAccountTypes()
      .pipe(first())
      .subscribe((res) => (this.accountTypes = res));
    this.userService
      .getTransactionTypes()
      .pipe(first())
      .subscribe((res) => (this.transactionsTypes = res));
    this.userService
      .getGenders()
      .pipe(first())
      .subscribe((res) => (this.genders = res));
  }
}
