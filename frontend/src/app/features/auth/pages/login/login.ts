import { ChangeDetectorRef, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './login.html',
  styleUrls: ['./login.css'],
})
export class Login {
  loginForm: FormGroup;
  message: string = '';
  messageType: 'success' | 'error' | '' = 'success';
  showPopup: boolean = false;
  showSelectionModal: boolean = false;
  tempCredentials: { email: string; password: string } | null = null;
  timeoutRef: any;
  showPassword = false;

  // Forgot Password Modal Fields
  showForgotPasswordModal = false;
  forgotPasswordForm: FormGroup;
  forgotMessage: string = '';
  forgotMessageType: 'success' | 'error' | '' = 'success';
  showForgotPopup: boolean = false;
  forgotToken: string = '';
  forgotTimeoutRef: any;

  togglePasswordVisibility() {
    this.showPassword = !this.showPassword;
  }

  openForgotPasswordModal() {
    this.forgotPasswordForm.reset();
    this.showForgotPasswordModal = true;
  }

  closeForgotPasswordModal() {
    this.showForgotPasswordModal = false;
  }

  onForgotPassword() {
    if (this.forgotTimeoutRef) {
      clearTimeout(this.forgotTimeoutRef);
    }

    if (this.forgotPasswordForm.invalid) {
      this.forgotPasswordForm.markAllAsTouched();
      return;
    }

    const { email } = this.forgotPasswordForm.value;

    this.authService.forgotPassword(email).subscribe({
      next: (response) => {
        const msg = response.message || '';
        this.forgotMessage = 'Reset link generated successfully! ✅';
        this.forgotMessageType = 'success';
        
        const match = msg.match(/token=([^\s&]+)/);
        if (match) {
          this.forgotToken = match[1];
        }
        
        this.showForgotPopup = true;
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.forgotMessage = error.error?.detail || error.message || 'Error requesting password reset ❌';
        this.forgotMessageType = 'error';
        this.showForgotPopup = true;
        this.forgotToken = '';
        
        this.forgotTimeoutRef = setTimeout(() => {
          this.showForgotPopup = false;
          this.cdr.detectChanges();
        }, 3000);
      }
    });
  }

  get forgotF() {
    return this.forgotPasswordForm.controls;
  }

  constructor(
    private readonly fb: FormBuilder,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef,
    private readonly authService: AuthService
  ) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
    });

    this.forgotPasswordForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
    });
  }

  onLogin() {
    if (this.timeoutRef) {
      clearTimeout(this.timeoutRef);
    }

    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    const { email, password } = this.loginForm.getRawValue();

    this.authService.login({ email, password }).subscribe({
      next: (response) => {
        if (response.requiresDashboardSelection) {
          this.tempCredentials = { email, password };
          this.showSelectionModal = true;
          this.cdr.detectChanges();
          return;
        }

        this.message = 'Login successful';
        this.messageType = 'success';
        this.showPopup = true;

        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          if (response.me) {
            this.router.navigate([this.authService.getLandingRoute(response.me.role)]);
          }
        }, 900);
      },
      error: (error) => {
        this.message = error.error?.detail || error.message || 'Invalid email or password';
        this.messageType = 'error';
        this.showPopup = true;

        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          this.cdr.detectChanges();
        }, 1600);
      }
    });
  }

  selectDashboard(mode: 'HR' | 'EMPLOYEE') {
    if (!this.tempCredentials) return;

    const { email, password } = this.tempCredentials;

    this.authService.login({ email, password, activeDashboard: mode }).subscribe({
      next: (response) => {
        this.showSelectionModal = false;
        this.tempCredentials = null;
        
        this.message = 'Login successful';
        this.messageType = 'success';
        this.showPopup = true;

        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          if (response.me) {
            this.router.navigate([this.authService.getLandingRoute(response.me.role)]);
          }
        }, 900);
      },
      error: (error) => {
        this.message = error.error?.detail || error.message || 'Error completing dashboard selection';
        this.messageType = 'error';
        this.showPopup = true;
        this.showSelectionModal = false;
        this.tempCredentials = null;

        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          this.cdr.detectChanges();
        }, 1600);
      }
    });
  }

  get f() {
    return this.loginForm.controls;
  }
}
