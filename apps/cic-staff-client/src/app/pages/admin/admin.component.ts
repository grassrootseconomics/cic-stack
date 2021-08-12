import { ChangeDetectionStrategy, Component, OnInit, ViewChild } from '@angular/core';
import { MatTableDataSource } from '@angular/material/table';
import { MatPaginator } from '@angular/material/paginator';
import { MatSort } from '@angular/material/sort';
import { LoggingService, UserService } from '@app/_services';
import { animate, state, style, transition, trigger } from '@angular/animations';
import { first } from 'rxjs/operators';
import { exportCsv } from '@app/_helpers';
import { Action } from '@app/_models';

@Component({
  selector: 'app-admin',
  templateUrl: './admin.component.html',
  styleUrls: ['./admin.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [
    trigger('detailExpand', [
      state('collapsed', style({ height: '0px', minHeight: 0, visibility: 'hidden' })),
      state('expanded', style({ height: '*', visibility: 'visible' })),
      transition('expanded <=> collapsed', animate('225ms cubic-bezier(0.4, 0.0, 0.2, 1)')),
    ]),
  ],
})
export class AdminComponent implements OnInit {
  dataSource: MatTableDataSource<any>;
  displayedColumns: Array<string> = ['expand', 'user', 'role', 'action', 'status', 'approve'];
  action: Action;
  actions: Array<Action>;
  loading: boolean = true;

  @ViewChild(MatPaginator) paginator: MatPaginator;
  @ViewChild(MatSort) sort: MatSort;

  constructor(private userService: UserService, private loggingService: LoggingService) {}

  ngOnInit(): void {
    this.userService.getActions();
    this.userService.actionsSubject.subscribe((actions) => {
      this.dataSource = new MatTableDataSource<any>(actions);
      this.dataSource.paginator = this.paginator;
      this.dataSource.sort = this.sort;
      this.actions = actions;
      if (actions.length > 0) {
        this.loading = false;
      }
    });
  }

  doFilter(value: string): void {
    this.dataSource.filter = value.trim().toLocaleLowerCase();
  }

  approvalStatus(status: boolean): string {
    return status ? 'Approved' : 'Unapproved';
  }

  approveAction(action: any): void {
    if (!confirm('Approve action?')) {
      return;
    }
    this.userService
      .approveAction(action.id)
      .pipe(first())
      .subscribe((res) => this.loggingService.sendInfoLevelMessage(res));
    this.userService.getActions();
  }

  disapproveAction(action: any): void {
    if (!confirm('Disapprove action?')) {
      return;
    }
    this.userService
      .revokeAction(action.id)
      .pipe(first())
      .subscribe((res) => this.loggingService.sendInfoLevelMessage(res));
    this.userService.getActions();
  }

  expandCollapse(row): void {
    row.isExpanded = !row.isExpanded;
  }

  downloadCsv(): void {
    exportCsv(this.actions, 'actions');
  }
}
