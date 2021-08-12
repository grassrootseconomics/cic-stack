import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccountsComponent } from './accounts.component';
import {
  FooterStubComponent,
  SidebarStubComponent,
  TopbarStubComponent,
  UserServiceStub,
} from '@src/testing';
import { AccountsModule } from '@pages/accounts/accounts.module';
import { AppModule } from '@app/app.module';
import { HttpClient } from '@angular/common/http';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { UserService } from '@app/_services';

describe('AccountsComponent', () => {
  let component: AccountsComponent;
  let fixture: ComponentFixture<AccountsComponent>;
  let httpClient: HttpClient;
  let httpTestingController: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [
        AccountsComponent,
        FooterStubComponent,
        SidebarStubComponent,
        TopbarStubComponent,
      ],
      imports: [AccountsModule, AppModule, HttpClientTestingModule],
      providers: [{ provide: UserService, useClass: UserServiceStub }],
    }).compileComponents();
    httpClient = TestBed.inject(HttpClient);
    httpTestingController = TestBed.inject(HttpTestingController);
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AccountsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
