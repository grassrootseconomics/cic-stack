import { Injectable } from '@angular/core';
import Web3 from 'web3';
import { environment } from '@src/environments/environment';

@Injectable({
  providedIn: 'root',
})
export class Web3Service {
  private static web3: Web3;

  constructor() {}

  public static getInstance(): Web3 {
    if (!Web3Service.web3) {
      Web3Service.web3 = new Web3(environment.web3Provider);
    }
    return Web3Service.web3;
  }
}
