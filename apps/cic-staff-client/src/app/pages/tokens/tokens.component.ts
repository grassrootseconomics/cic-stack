import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  OnInit,
  ViewChild,
} from '@angular/core';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { TokenService } from '@app/_services';
import { MatTableDataSource } from '@angular/material/table';
import { exportCsv } from '@app/_helpers';
import { Token } from '@app/_models';

@Component({
  selector: 'app-tokens',
  templateUrl: './tokens.component.html',
  styleUrls: ['./tokens.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TokensComponent implements OnInit, AfterViewInit {
  dataSource: MatTableDataSource<any>;
  columnsToDisplay: Array<string> = ['name', 'symbol', 'address', 'supply'];
  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;
  tokens: Array<Token>;
  token: Token;
  loading: boolean = true;

  constructor(private tokenService: TokenService) {}

  ngOnInit(): void {
    this.tokenService.load.subscribe(async (status: boolean) => {
      if (status) {
        await this.tokenService.getTokens();
      }
    });
    this.tokenService.tokensSubject.subscribe((tokens) => {
      this.dataSource = new MatTableDataSource(tokens);
      this.dataSource.paginator = this.paginator;
      this.dataSource.sort = this.sort;
      this.tokens = tokens;
      if (tokens.length > 0) {
        this.loading = false;
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

  viewToken(token): void {
    this.token = token;
  }

  downloadCsv(): void {
    exportCsv(this.tokens, 'tokens');
  }
}
