import { TestBed } from '@angular/core/testing';

import { BlockSyncService } from '@app/_services/block-sync.service';
import { TransactionService } from '@app/_services/transaction.service';
import { TransactionServiceStub } from '@src/testing';

describe('BlockSyncService', () => {
  let service: BlockSyncService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [{ provide: TransactionService, useClass: TransactionServiceStub }],
    });
    service = TestBed.inject(BlockSyncService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
