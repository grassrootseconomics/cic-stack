import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'unixDate',
})
export class UnixDatePipe implements PipeTransform {
  transform(timestamp: number, ...args: unknown[]): any {
    return new Date(timestamp * 1000).toLocaleDateString('en-GB');
  }
}
