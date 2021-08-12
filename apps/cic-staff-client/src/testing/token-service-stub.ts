export class TokenServiceStub {
  getBySymbol(symbol: string): any {
    return {
      name: 'Reserve',
      symbol: 'RSV',
    };
  }
}
