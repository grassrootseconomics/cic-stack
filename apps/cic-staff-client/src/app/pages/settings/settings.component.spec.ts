import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SettingsComponent } from '@pages/settings/settings.component';
import { FooterStubComponent, SidebarStubComponent, TopbarStubComponent } from '@src/testing';
import { SettingsModule } from '@pages/settings/settings.module';
import { AppModule } from '@app/app.module';

describe('SettingsComponent', () => {
  let component: SettingsComponent;
  let fixture: ComponentFixture<SettingsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [
        SettingsComponent,
        FooterStubComponent,
        SidebarStubComponent,
        TopbarStubComponent,
      ],
      imports: [AppModule, SettingsModule],
    }).compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(SettingsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
