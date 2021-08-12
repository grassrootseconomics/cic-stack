import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TokenDetailsComponent } from '@pages/tokens/token-details/token-details.component';
import {
  ActivatedRouteStub,
  FooterStubComponent,
  SidebarStubComponent,
  TokenServiceStub,
  TopbarStubComponent,
} from '@src/testing';
import { ActivatedRoute } from '@angular/router';
import { TokenService } from '@app/_services';
import { TokensModule } from '@pages/tokens/tokens.module';
import { AppModule } from '@app/app.module';

describe('TokenDetailsComponent', () => {
  let component: TokenDetailsComponent;
  let fixture: ComponentFixture<TokenDetailsComponent>;
  let route: ActivatedRouteStub;

  beforeEach(async () => {
    route = new ActivatedRouteStub();
    route.setParamMap({ id: 'test' });
    await TestBed.configureTestingModule({
      declarations: [
        TokenDetailsComponent,
        FooterStubComponent,
        SidebarStubComponent,
        TopbarStubComponent,
      ],
      providers: [
        { provide: ActivatedRoute, useValue: route },
        { provide: TokenService, useClass: TokenServiceStub },
      ],
      imports: [AppModule, TokensModule],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(TokenDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
