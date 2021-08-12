import {
  Component,
  OnInit,
  ChangeDetectionStrategy,
  Input,
  Output,
  EventEmitter,
  SimpleChanges,
  OnChanges,
} from '@angular/core';
const vCard = require('vcard-parser');

@Component({
  selector: 'app-account-history',
  templateUrl: './account-history.component.html',
  styleUrls: ['./account-history.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccountHistoryComponent implements OnInit, OnChanges {
  @Input() account;

  @Output() closeWindow: EventEmitter<any> = new EventEmitter<any>();

  constructor() {}

  ngOnInit(): void {}

  ngOnChanges(changes: SimpleChanges): void {
    if (this.account) {
      this.account.vcard = vCard.parse(atob(this.account.vcard));
    }
  }

  close(): void {
    this.account = null;
    this.closeWindow.emit(this.account);
  }
}
