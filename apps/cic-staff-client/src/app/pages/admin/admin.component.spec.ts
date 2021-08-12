import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AdminComponent } from '@pages/admin/admin.component';
import { HttpClient } from '@angular/common/http';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { AdminModule } from '@pages/admin/admin.module';
import {
  FooterStubComponent,
  SidebarStubComponent,
  TopbarStubComponent,
  UserServiceStub,
} from '@src/testing';
import { AppModule } from '@app/app.module';
import { UserService } from '@app/_services';

describe('AdminComponent', () => {
  let component: AdminComponent;
  let fixture: ComponentFixture<AdminComponent>;
  let httpClient: HttpClient;
  let httpTestingController: HttpTestingController;
  let userService: UserServiceStub;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [
        AdminComponent,
        FooterStubComponent,
        SidebarStubComponent,
        TopbarStubComponent,
      ],
      imports: [AdminModule, AppModule, HttpClientTestingModule],
      providers: [{ provide: UserService, useClass: UserServiceStub }],
    }).compileComponents();
    httpClient = TestBed.inject(HttpClient);
    httpTestingController = TestBed.inject(HttpTestingController);
    userService = new UserServiceStub();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AdminComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('#approveAction should toggle approval status', () => {
    const action = userService.getActionById('1');
    expect(action).toBe({
      id: 1,
      user: 'Tom',
      role: 'enroller',
      action: 'Disburse RSV 100',
      approval: false,
    });
  });
});
