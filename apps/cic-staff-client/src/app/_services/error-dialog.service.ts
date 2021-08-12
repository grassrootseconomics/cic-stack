import { Injectable } from '@angular/core';
import { MatDialog, MatDialogRef } from '@angular/material/dialog';
import { ErrorDialogComponent } from '@app/shared/error-dialog/error-dialog.component';

@Injectable({
  providedIn: 'root',
})
export class ErrorDialogService {
  public isDialogOpen: boolean = false;

  constructor(public dialog: MatDialog) {}

  openDialog(data): any {
    if (this.isDialogOpen) {
      return false;
    }
    this.isDialogOpen = true;
    const dialogRef: MatDialogRef<any> = this.dialog.open(ErrorDialogComponent, {
      width: '300px',
      data,
    });

    dialogRef.afterClosed().subscribe(() => (this.isDialogOpen = false));
  }
}
