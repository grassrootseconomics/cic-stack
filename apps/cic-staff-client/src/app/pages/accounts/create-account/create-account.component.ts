import { ChangeDetectionStrategy, Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { LocationService, UserService } from '@app/_services';
import { CustomErrorStateMatcher } from '@app/_helpers';
import { first } from 'rxjs/operators';

@Component({
  selector: 'app-create-account',
  templateUrl: './create-account.component.html',
  styleUrls: ['./create-account.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CreateAccountComponent implements OnInit {
  createForm: FormGroup;
  matcher: CustomErrorStateMatcher = new CustomErrorStateMatcher();
  submitted: boolean = false;
  categories: Array<string>;
  areaNames: Array<string>;
  accountTypes: Array<string>;
  genders: Array<string>;

  constructor(
    private formBuilder: FormBuilder,
    private locationService: LocationService,
    private userService: UserService
  ) {}

  ngOnInit(): void {
    this.createForm = this.formBuilder.group({
      accountType: ['', Validators.required],
      idNumber: ['', Validators.required],
      phoneNumber: ['', Validators.required],
      givenName: ['', Validators.required],
      surname: ['', Validators.required],
      directoryEntry: ['', Validators.required],
      location: ['', Validators.required],
      gender: ['', Validators.required],
      referrer: ['', Validators.required],
      businessCategory: ['', Validators.required],
    });
    this.loadSearchData();
  }

  get createFormStub(): any {
    return this.createForm.controls;
  }

  onSubmit(): void {
    this.submitted = true;
    if (this.createForm.invalid || !confirm('Create account?')) {
      return;
    }
    this.submitted = false;
  }

  loadSearchData(): void {
    this.userService.getCategories();
    this.userService.categoriesSubject.subscribe((res) => {
      this.categories = Object.keys(res);
    });
    this.locationService.getAreaNames();
    this.locationService.areaNamesSubject.subscribe((res) => {
      this.areaNames = Object.keys(res);
    });
    this.userService
      .getAccountTypes()
      .pipe(first())
      .subscribe((res) => (this.accountTypes = res));
    this.userService
      .getGenders()
      .pipe(first())
      .subscribe((res) => (this.genders = res));
  }
}
