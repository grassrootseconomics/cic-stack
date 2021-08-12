import { ChangeDetectionStrategy, Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { CustomErrorStateMatcher } from '@app/_helpers';
import { AuthService } from '@app/_services';
import { ErrorDialogService } from '@app/_services/error-dialog.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-auth',
  templateUrl: './auth.component.html',
  styleUrls: ['./auth.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthComponent implements OnInit {
  keyForm: FormGroup;
  submitted: boolean = false;
  loading: boolean = false;
  matcher: CustomErrorStateMatcher = new CustomErrorStateMatcher();

  constructor(
    private authService: AuthService,
    private formBuilder: FormBuilder,
    private router: Router,
    private errorDialogService: ErrorDialogService
  ) {}

  ngOnInit(): void {
    this.keyForm = this.formBuilder.group({
      key: ['', Validators.required],
    });
    if (this.authService.getPrivateKey()) {
      this.authService.loginView();
    }
  }

  get keyFormStub(): any {
    return this.keyForm.controls;
  }

  async onSubmit(): Promise<void> {
    this.submitted = true;

    if (this.keyForm.invalid) {
      return;
    }

    this.loading = true;
    await this.authService.setKey(this.keyFormStub.key.value);
    this.loading = false;
  }

  async login(): Promise<void> {
    try {
      const loginResult = await this.authService.login();
      if (loginResult) {
        this.router.navigate(['/home']);
      }
    } catch (HttpError) {
      this.errorDialogService.openDialog({
        message: 'Failed to login please try again.',
      });
    }
  }

  switchWindows(): void {
    const divOne: HTMLElement = document.getElementById('one');
    const divTwo: HTMLElement = document.getElementById('two');
    this.toggleDisplay(divOne);
    this.toggleDisplay(divTwo);
  }

  toggleDisplay(element: any): void {
    const style: string = window.getComputedStyle(element).display;
    if (style === 'block') {
      element.style.display = 'none';
    } else {
      element.style.display = 'block';
    }
  }
}
