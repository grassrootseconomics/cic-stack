import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TokensComponent } from '@pages/tokens/tokens.component';
import { FooterStubComponent, SidebarStubComponent, TopbarStubComponent } from '@src/testing';
import { AppModule } from '@app/app.module';
import { TokensModule } from '@pages/tokens/tokens.module';

describe('TokensComponent', () => {
  let component: TokensComponent;
  let fixture: ComponentFixture<TokensComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [
        TokensComponent,
        FooterStubComponent,
        SidebarStubComponent,
        TopbarStubComponent,
      ],
      imports: [AppModule, TokensModule],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TokensComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
