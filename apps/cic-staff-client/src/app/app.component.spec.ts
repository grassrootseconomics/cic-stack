import { TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { AppComponent } from '@app/app.component';
import { TransactionService } from '@app/_services';
import {
  FooterStubComponent,
  SidebarStubComponent,
  TopbarStubComponent,
  TransactionServiceStub,
} from '@src/testing';

describe('AppComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RouterTestingModule],
      declarations: [AppComponent, FooterStubComponent, SidebarStubComponent, TopbarStubComponent],
      providers: [{ provide: TransactionService, useClass: TransactionServiceStub }],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it(`should have as title 'cic-staff-client'`, () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app.title).toEqual('cic-staff-client');
  });
});
