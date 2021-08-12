import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'tokenRatio' })
export class TokenRatioPipe implements PipeTransform {
  transform(value: any = 0, ...args): any {
    return Number(value) / Math.pow(10, 6);
  }
}
