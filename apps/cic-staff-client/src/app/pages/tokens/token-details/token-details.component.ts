import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnInit,
  Output,
} from '@angular/core';
import { Token } from '@app/_models';

@Component({
  selector: 'app-token-details',
  templateUrl: './token-details.component.html',
  styleUrls: ['./token-details.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TokenDetailsComponent implements OnInit {
  @Input() token: Token;

  @Output() closeWindow: EventEmitter<any> = new EventEmitter<any>();

  constructor() {}

  ngOnInit(): void {}

  close(): void {
    this.token = null;
    this.closeWindow.emit(this.token);
  }
}
