import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CreateAccountComponent } from '@pages/accounts/create-account/create-account.component';
import { AccountsModule } from '@pages/accounts/accounts.module';
import { AppModule } from '@app/app.module';
import { FooterStubComponent, SidebarStubComponent, TopbarStubComponent } from '@src/testing';

describe('CreateAccountComponent', () => {
  let component: CreateAccountComponent;
  let fixture: ComponentFixture<CreateAccountComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [
        CreateAccountComponent,
        FooterStubComponent,
        SidebarStubComponent,
        TopbarStubComponent,
      ],
      imports: [AccountsModule, AppModule],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(CreateAccountComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
