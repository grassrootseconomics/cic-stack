import { Injectable } from '@angular/core';
import { CICRegistry } from '@cicnet/cic-client';
import { TokenRegistry } from '@app/_eth';
import { RegistryService } from '@app/_services/registry.service';
import { Token } from '@app/_models';
import { BehaviorSubject, Observable, Subject } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class TokenService {
  registry: CICRegistry;
  tokenRegistry: TokenRegistry;
  tokens: Array<Token> = [];
  private tokensList: BehaviorSubject<Array<Token>> = new BehaviorSubject<Array<Token>>(
    this.tokens
  );
  tokensSubject: Observable<Array<Token>> = this.tokensList.asObservable();
  load: BehaviorSubject<any> = new BehaviorSubject<any>(false);

  constructor() {}

  async init(): Promise<void> {
    this.registry = await RegistryService.getRegistry();
    this.tokenRegistry = await RegistryService.getTokenRegistry();
    this.load.next(true);
  }

  addToken(token: Token): void {
    const savedIndex = this.tokens.findIndex((tk) => tk.address === token.address);
    if (savedIndex === 0) {
      return;
    }
    if (savedIndex > 0) {
      this.tokens.splice(savedIndex, 1);
    }
    this.tokens.unshift(token);
    this.tokensList.next(this.tokens);
  }

  async getTokens(): Promise<void> {
    const count: number = await this.tokenRegistry.totalTokens();
    for (let i = 0; i < count; i++) {
      const token: Token = await this.getTokenByAddress(await this.tokenRegistry.entry(i));
      this.addToken(token);
    }
  }

  async getTokenByAddress(address: string): Promise<Token> {
    const token: any = {};
    const tokenContract = await this.registry.addToken(address);
    token.address = address;
    token.name = await tokenContract.methods.name().call();
    token.symbol = await tokenContract.methods.symbol().call();
    token.supply = await tokenContract.methods.totalSupply().call();
    token.decimals = await tokenContract.methods.decimals().call();
    return token;
  }

  async getTokenBySymbol(symbol: string): Promise<Observable<Token>> {
    const tokenSubject: Subject<Token> = new Subject<Token>();
    await this.getTokens();
    this.tokensSubject.subscribe((tokens) => {
      const queriedToken = tokens.find((token) => token.symbol === symbol);
      tokenSubject.next(queriedToken);
    });
    return tokenSubject.asObservable();
  }

  async getTokenBalance(address: string): Promise<(address: string) => Promise<number>> {
    const token = await this.registry.addToken(await this.tokenRegistry.entry(0));
    return await token.methods.balanceOf(address).call();
  }

  async getTokenName(): Promise<string> {
    const token = await this.registry.addToken(await this.tokenRegistry.entry(0));
    return await token.methods.name().call();
  }

  async getTokenSymbol(): Promise<string> {
    const token = await this.registry.addToken(await this.tokenRegistry.entry(0));
    return await token.methods.symbol().call();
  }
}
