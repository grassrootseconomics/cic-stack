import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TransactionsComponent } from '@pages/transactions/transactions.component';
import { HttpClient } from '@angular/common/http';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { FooterStubComponent, SidebarStubComponent, TopbarStubComponent } from '@src/testing';
import { TransactionsModule } from '@pages/transactions/transactions.module';
import { AppModule } from '@app/app.module';

describe('TransactionsComponent', () => {
  let component: TransactionsComponent;
  let fixture: ComponentFixture<TransactionsComponent>;
  let httpClient: HttpClient;
  let httpTestingController: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [
        TransactionsComponent,
        FooterStubComponent,
        SidebarStubComponent,
        TopbarStubComponent,
      ],
      imports: [AppModule, HttpClientTestingModule, TransactionsModule],
    }).compileComponents();
    httpClient = TestBed.inject(HttpClient);
    httpTestingController = TestBed.inject(HttpTestingController);
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TransactionsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
