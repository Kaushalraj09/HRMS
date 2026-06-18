import { ChangeDetectorRef, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';

// Hot-reload trigger comment to force server compilation refresh
@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './reset-password.html',
  styleUrls: ['./reset-password.css'],
})
export class ResetPassword implements OnInit {
  resetPasswordForm: FormGroup;
  message: string = '';
  messageType: 'success' | 'error' | '' = 'success';
  showPopup: boolean = false;
  token: string = '';
  timeoutRef: any;

  constructor(
    private readonly fb: FormBuilder,
    private readonly router: Router,
    private readonly route: ActivatedRoute,
    private readonly cdr: ChangeDetectorRef,
    private readonly authService: AuthService
  ) {
    this.resetPasswordForm = this.fb.group({
      newPassword: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', [Validators.required]],
    }, { validators: this.passwordMatchValidator });
  }

  ngOnInit() {
    this.route.queryParams.subscribe(params => {
      this.token = params['token'] || '';
    });
  }

  passwordMatchValidator(g: FormGroup) {
    const newPass = g.get('newPassword')?.value;
    const confirmPass = g.get('confirmPassword')?.value;
    return newPass === confirmPass ? null : { mismatch: true };
  }

  onResetPassword() {
    if (this.timeoutRef) {
      clearTimeout(this.timeoutRef);
    }

    if (this.resetPasswordForm.invalid) {
      this.resetPasswordForm.markAllAsTouched();
      return;
    }

    if (!this.token) {
      this.message = 'Reset token is missing from URL! Please request a new link ❌';
      this.messageType = 'error';
      this.showPopup = true;
      return;
    }

    const { newPassword, confirmPassword } = this.resetPasswordForm.value;

    this.authService.resetPassword({
      token: this.token,
      newPassword,
      confirmPassword
    }).subscribe({
      next: (response) => {
        this.message = 'Password reset successfully! Redirecting to login... ✅';
        this.messageType = 'success';
        this.showPopup = true;
        this.cdr.detectChanges();

        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          this.router.navigate(['/auth/login']);
        }, 2000);
      },
      error: (error) => {
        this.message = error.error?.detail || error.message || 'Failed to reset password ❌';
        this.messageType = 'error';
        this.showPopup = true;
        this.cdr.detectChanges();

        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          this.cdr.detectChanges();
        }, 3000);
      }
    });
  }

  get f() {
    return this.resetPasswordForm.controls;
  }
}
