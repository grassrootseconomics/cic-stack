import { Injectable } from '@angular/core';
import { Settings } from '@app/_models';
import { TransactionHelper } from '@cicnet/cic-client';
import { first } from 'rxjs/operators';
import { TransactionService } from '@app/_services/transaction.service';
import { environment } from '@src/environments/environment';
import { RegistryService } from '@app/_services/registry.service';
import { Web3Service } from '@app/_services/web3.service';

@Injectable({
  providedIn: 'root',
})
export class BlockSyncService {
  readyStateTarget: number = 2;
  readyState: number = 0;

  constructor(private transactionService: TransactionService) {}

  async blockSync(address: string = null, offset: number = 0, limit: number = 100): Promise<void> {
    const settings: Settings = new Settings(this.scan);
    const readyStateElements: { network: number } = { network: 2 };
    settings.w3.provider = environment.web3Provider;
    settings.w3.engine = Web3Service.getInstance();
    settings.registry = await RegistryService.getRegistry();
    settings.txHelper = new TransactionHelper(settings.w3.engine, settings.registry);

    settings.txHelper.ontransfer = async (transaction: any): Promise<void> => {
      window.dispatchEvent(this.newEvent(transaction, 'cic_transfer'));
    };
    settings.txHelper.onconversion = async (transaction: any): Promise<any> => {
      window.dispatchEvent(this.newEvent(transaction, 'cic_convert'));
    };
    this.readyStateProcessor(settings, readyStateElements.network, address, offset, limit);
  }

  readyStateProcessor(
    settings: Settings,
    bit: number,
    address: string,
    offset: number,
    limit: number
  ): void {
    // tslint:disable-next-line:no-bitwise
    this.readyState |= bit;
    if (this.readyStateTarget === this.readyState && this.readyStateTarget) {
      const wHeadSync: Worker = new Worker('./../assets/js/block-sync/head.js');
      wHeadSync.onmessage = (m) => {
        settings.txHelper.processReceipt(m.data);
      };
      wHeadSync.postMessage({
        w3_provider: settings.w3.provider,
      });
      if (address === null) {
        this.transactionService
          .getAllTransactions(offset, limit)
          .pipe(first())
          .subscribe((res) => {
            this.fetcher(settings, res);
          });
      } else {
        this.transactionService
          .getAddressTransactions(address, offset, limit)
          .pipe(first())
          .subscribe((res) => {
            this.fetcher(settings, res);
          });
      }
    }
  }

  newEvent(tx: any, eventType: string): any {
    return new CustomEvent(eventType, {
      detail: {
        tx,
      },
    });
  }

  async scan(
    settings: Settings,
    lo: number,
    hi: number,
    bloomBlockBytes: Uint8Array,
    bloomBlocktxBytes: Uint8Array,
    bloomRounds: any
  ): Promise<void> {
    const w: Worker = new Worker('./../assets/js/block-sync/ondemand.js');
    w.onmessage = (m) => {
      settings.txHelper.processReceipt(m.data);
    };
    w.postMessage({
      w3_provider: settings.w3.provider,
      lo,
      hi,
      filters: [bloomBlockBytes, bloomBlocktxBytes],
      filter_rounds: bloomRounds,
    });
  }

  fetcher(settings: Settings, transactionsInfo: any): void {
    const blockFilterBinstr: string = window.atob(transactionsInfo.block_filter);
    const bOne: Uint8Array = new Uint8Array(blockFilterBinstr.length);
    bOne.map((e, i, v) => (v[i] = blockFilterBinstr.charCodeAt(i)));

    const blocktxFilterBinstr: string = window.atob(transactionsInfo.blocktx_filter);
    const bTwo: Uint8Array = new Uint8Array(blocktxFilterBinstr.length);
    bTwo.map((e, i, v) => (v[i] = blocktxFilterBinstr.charCodeAt(i)));

    settings.scanFilter(
      settings,
      transactionsInfo.low,
      transactionsInfo.high,
      bOne,
      bTwo,
      transactionsInfo.filter_rounds
    );
  }
}
