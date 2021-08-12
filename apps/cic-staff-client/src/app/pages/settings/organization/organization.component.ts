import { ChangeDetectionStrategy, Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { CustomErrorStateMatcher } from '@app/_helpers';

@Component({
  selector: 'app-organization',
  templateUrl: './organization.component.html',
  styleUrls: ['./organization.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OrganizationComponent implements OnInit {
  organizationForm: FormGroup;
  submitted: boolean = false;
  matcher: CustomErrorStateMatcher = new CustomErrorStateMatcher();

  constructor(private formBuilder: FormBuilder) {}

  ngOnInit(): void {
    this.organizationForm = this.formBuilder.group({
      disbursement: ['', Validators.required],
      transfer: '',
      countryCode: ['', Validators.required],
    });
  }

  get organizationFormStub(): any {
    return this.organizationForm.controls;
  }

  onSubmit(): void {
    this.submitted = true;
    if (this.organizationForm.invalid || !confirm('Set organization information?')) {
      return;
    }
    this.submitted = false;
  }
}
