import { ChangeDetectionStrategy, Component, OnInit, ViewChild } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { AuthService } from '@app/_services';
import { Staff } from '@app/_models/staff';
import { exportCsv } from '@app/_helpers';

@Component({
  selector: 'app-settings',
  templateUrl: './settings.component.html',
  styleUrls: ['./settings.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsComponent implements OnInit {
  dataSource: MatTableDataSource<any>;
  displayedColumns: Array<string> = ['name', 'email', 'userId'];
  trustedUsers: Array<Staff>;
  userInfo: Staff;
  loading: boolean = true;

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  constructor(private authService: AuthService) {}

  ngOnInit(): void {
    this.authService.trustedUsersSubject.subscribe((users) => {
      this.dataSource = new MatTableDataSource<any>(users);
      this.dataSource.paginator = this.paginator;
      this.dataSource.sort = this.sort;
      this.trustedUsers = users;
      if (users.length > 0) {
        this.loading = false;
      }
    });
    this.userInfo = this.authService.getPrivateKeyInfo();
  }

  doFilter(value: string): void {
    this.dataSource.filter = value.trim().toLocaleLowerCase();
  }

  downloadCsv(): void {
    exportCsv(this.trustedUsers, 'users');
  }

  logout(): void {
    this.authService.logout();
  }
}
