import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AccountDetailsComponent } from '@pages/accounts/account-details/account-details.component';
import { HttpClient } from '@angular/common/http';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { ActivatedRoute } from '@angular/router';
import { AccountsModule } from '@pages/accounts/accounts.module';
import { UserService } from '@app/_services';
import { AppModule } from '@app/app.module';
import {
  ActivatedRouteStub,
  FooterStubComponent,
  SidebarStubComponent,
  TopbarStubComponent,
  UserServiceStub,
} from '@src/testing';

describe('AccountDetailsComponent', () => {
  let component: AccountDetailsComponent;
  let fixture: ComponentFixture<AccountDetailsComponent>;
  let httpClient: HttpClient;
  let httpTestingController: HttpTestingController;
  let route: ActivatedRouteStub;

  beforeEach(async () => {
    route = new ActivatedRouteStub();
    route.setParamMap({ id: 'test' });
    await TestBed.configureTestingModule({
      declarations: [
        AccountDetailsComponent,
        FooterStubComponent,
        SidebarStubComponent,
        TopbarStubComponent,
      ],
      imports: [AccountsModule, AppModule, HttpClientTestingModule],
      providers: [
        { provide: ActivatedRoute, useValue: route },
        { provide: UserService, useClass: UserServiceStub },
      ],
    }).compileComponents();
    httpClient = TestBed.inject(HttpClient);
    httpTestingController = TestBed.inject(HttpTestingController);
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AccountDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
