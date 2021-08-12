import { Component, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { CustomErrorStateMatcher } from '@app/_helpers';
import { UserService } from '@app/_services';
import { Router } from '@angular/router';
import { strip0x } from '@src/assets/js/ethtx/dist/hex';
import { environment } from '@src/environments/environment';

@Component({
  selector: 'app-account-search',
  templateUrl: './account-search.component.html',
  styleUrls: ['./account-search.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AccountSearchComponent implements OnInit {
  phoneSearchForm: FormGroup;
  phoneSearchSubmitted: boolean = false;
  phoneSearchLoading: boolean = false;
  addressSearchForm: FormGroup;
  addressSearchSubmitted: boolean = false;
  addressSearchLoading: boolean = false;
  matcher: CustomErrorStateMatcher = new CustomErrorStateMatcher();

  constructor(
    private formBuilder: FormBuilder,
    private userService: UserService,
    private router: Router
  ) {
    this.phoneSearchForm = this.formBuilder.group({
      phoneNumber: ['', Validators.required],
    });
    this.addressSearchForm = this.formBuilder.group({
      address: ['', Validators.required],
    });
  }

  ngOnInit(): void {}

  get phoneSearchFormStub(): any {
    return this.phoneSearchForm.controls;
  }
  get addressSearchFormStub(): any {
    return this.addressSearchForm.controls;
  }

  async onPhoneSearch(): Promise<void> {
    this.phoneSearchSubmitted = true;
    if (this.phoneSearchForm.invalid) {
      return;
    }
    this.phoneSearchLoading = true;
    (
      await this.userService.getAccountByPhone(this.phoneSearchFormStub.phoneNumber.value, 100)
    ).subscribe(async (res) => {
      if (res !== undefined) {
        await this.router.navigateByUrl(
          `/accounts/${strip0x(res.identities.evm[`bloxberg:${environment.bloxbergChainId}`][0])}`
        );
      } else {
        alert('Account not found!');
      }
    });
    this.phoneSearchLoading = false;
  }

  async onAddressSearch(): Promise<void> {
    this.addressSearchSubmitted = true;
    if (this.addressSearchForm.invalid) {
      return;
    }
    this.addressSearchLoading = true;
    (
      await this.userService.getAccountByAddress(this.addressSearchFormStub.address.value, 100)
    ).subscribe(async (res) => {
      if (res !== undefined) {
        await this.router.navigateByUrl(
          `/accounts/${strip0x(res.identities.evm[`bloxberg:${environment.bloxbergChainId}`][0])}`
        );
      } else {
        alert('Account not found!');
      }
    });
    this.addressSearchLoading = false;
  }
}
