import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
} from '@angular/core';
import { Router } from '@angular/router';
import { TokenService, TransactionService } from '@app/_services';
import { copyToClipboard } from '@app/_helpers';
import { MatSnackBar } from '@angular/material/snack-bar';
import { strip0x } from '@src/assets/js/ethtx/dist/hex';

@Component({
  selector: 'app-transaction-details',
  templateUrl: './transaction-details.component.html',
  styleUrls: ['./transaction-details.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TransactionDetailsComponent implements OnInit {
  @Input() transaction;

  @Output() closeWindow: EventEmitter<any> = new EventEmitter<any>();

  senderBloxbergLink: string;
  recipientBloxbergLink: string;
  traderBloxbergLink: string;
  tokenName: string;
  tokenSymbol: string;

  constructor(
    private router: Router,
    private transactionService: TransactionService,
    private snackBar: MatSnackBar,
    private tokenService: TokenService
  ) {}

  ngOnInit(): void {
    if (this.transaction?.type === 'conversion') {
      this.traderBloxbergLink =
        'https://blockexplorer.bloxberg.org/address/' + this.transaction?.trader + '/transactions';
    } else {
      this.senderBloxbergLink =
        'https://blockexplorer.bloxberg.org/address/' + this.transaction?.from + '/transactions';
      this.recipientBloxbergLink =
        'https://blockexplorer.bloxberg.org/address/' + this.transaction?.to + '/transactions';
    }
    this.tokenService.load.subscribe(async (status: boolean) => {
      if (status) {
        this.tokenSymbol = await this.tokenService.getTokenSymbol();
        this.tokenName = await this.tokenService.getTokenName();
      }
    });
  }

  async viewSender(): Promise<void> {
    await this.router.navigateByUrl(`/accounts/${strip0x(this.transaction.from)}`);
  }

  async viewRecipient(): Promise<void> {
    await this.router.navigateByUrl(`/accounts/${strip0x(this.transaction.to)}`);
  }

  async viewTrader(): Promise<void> {
    await this.router.navigateByUrl(`/accounts/${strip0x(this.transaction.trader)}`);
  }

  async reverseTransaction(): Promise<void> {
    await this.transactionService.transferRequest(
      this.transaction.token.address,
      this.transaction.to,
      this.transaction.from,
      this.transaction.value
    );
  }

  copyAddress(address: string): void {
    if (copyToClipboard(address)) {
      this.snackBar.open(address + ' copied successfully!', 'Close', { duration: 3000 });
    }
  }

  close(): void {
    this.transaction = null;
    this.closeWindow.emit(this.transaction);
  }
}
