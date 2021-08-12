import { ComponentFixture, TestBed } from '@angular/core/testing';

import { OrganizationComponent } from '@pages/settings/organization/organization.component';
import { FooterStubComponent, SidebarStubComponent, TopbarStubComponent } from '@src/testing';
import { SettingsModule } from '@pages/settings/settings.module';
import { AppModule } from '@app/app.module';

describe('OrganizationComponent', () => {
  let component: OrganizationComponent;
  let fixture: ComponentFixture<OrganizationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [
        OrganizationComponent,
        FooterStubComponent,
        SidebarStubComponent,
        TopbarStubComponent,
      ],
      imports: [AppModule, SettingsModule],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(OrganizationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
