import { ChangeDetectorRef, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, Validators, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './forgot-password.html',
  styleUrls: ['./forgot-password.css'],
})
export class ForgotPassword {
  forgotPasswordForm: FormGroup;
  message: string = '';
  messageType: 'success' | 'error' | '' = 'success';
  showPopup: boolean = false;
  token: string = '';
  timeoutRef: any;

  constructor(
    private readonly fb: FormBuilder,
    private readonly router: Router,
    private readonly cdr: ChangeDetectorRef,
    private readonly authService: AuthService
  ) {
    this.forgotPasswordForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
    });
  }

  onForgotPassword() {
    if (this.timeoutRef) {
      clearTimeout(this.timeoutRef);
    }

    if (this.forgotPasswordForm.invalid) {
      this.forgotPasswordForm.markAllAsTouched();
      return;
    }

    const { email } = this.forgotPasswordForm.value;

    this.authService.forgotPassword(email).subscribe({
      next: (response) => {
        const msg = response.message || '';
        this.message = msg || 'If the account exists, recovery instructions have been sent. ✅';
        this.messageType = 'success';
        
        // Extract the token from the response message if present
        const match = msg.match(/token=([^\s&]+)/);
        if (match) {
          this.token = match[1];
        }
        
        this.showPopup = true;
        this.cdr.detectChanges();
      },
      error: (error) => {
        this.message = error.error?.detail || error.message || 'Error requesting password reset ❌';
        this.messageType = 'error';
        this.showPopup = true;
        this.token = '';
        
        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          this.cdr.detectChanges();
        }, 3000);
      }
    });
  }

  get f() {
    return this.forgotPasswordForm.controls;
  }
}
