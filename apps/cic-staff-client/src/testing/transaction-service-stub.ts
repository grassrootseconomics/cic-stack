import { Observable, of } from 'rxjs';

export class TransactionServiceStub {
  setTransaction(transaction: any, cacheSize: number): void {}

  setConversion(conversion: any): void {}

  getAllTransactions(offset: number, limit: number): Observable<any> {
    return of('Hello World');
  }
}
