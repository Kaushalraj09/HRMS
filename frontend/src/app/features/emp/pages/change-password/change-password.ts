import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, AbstractControl, ValidationErrors, ReactiveFormsModule } from '@angular/forms';
import { ChangePasswordService } from './change-password.service';

export function passwordStrengthValidator(control: AbstractControl): ValidationErrors | null {
  const value = control.value;
  if (!value) return null;

  const hasLetters = /[a-zA-Z]/.test(value);
  const hasNumbers = /[0-9]/.test(value);
  const isLengthValid = value.length >= 8;

  const valid = hasLetters && hasNumbers && isLengthValid;
  if (!valid) {
    return { invalidPasswordOptions: true };
  }
  return null;
}

export function matchPasswordValidator(control: AbstractControl): ValidationErrors | null {
  const newPassword = control.get('newPassword')?.value;
  const confirmPassword = control.get('confirmPassword')?.value;

  if (newPassword !== confirmPassword) {
    control.get('confirmPassword')?.setErrors({ mismatchedPasswords: true });
    return { mismatchedPasswords: true };
  } else {
    // Clear the error gracefully to not break required status completely
    if (control.get('confirmPassword')?.hasError('mismatchedPasswords')) {
        control.get('confirmPassword')?.setErrors(null);
    }
  }
  return null;
}

@Component({
  selector: 'app-change-password',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './change-password.html',
  styleUrl: './change-password.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ChangePasswordComponent {
  passwordForm: FormGroup;
  isLoading = false;
  successMessage = '';
  errorMessage = '';

  showCurrent = false;
  showNew = false;
  showConfirm = false;

  constructor(private fb: FormBuilder, private changePasswordService: ChangePasswordService) {
    this.passwordForm = this.fb.group({
      currentPassword: ['', Validators.required],
      newPassword: ['', [Validators.required, passwordStrengthValidator]],
      confirmPassword: ['', Validators.required]
    }, { validators: matchPasswordValidator });
  }

  get passwordStrength(): string {
    const pw = this.passwordForm.get('newPassword')?.value || '';
    if (!pw) return '';
    if (pw.length < 8) return 'Weak';
    const hasLetters = /[a-zA-Z]/.test(pw);
    const hasNumbers = /[0-9]/.test(pw);
    const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(pw);
    
    let strength = 0;
    if (pw.length >= 8) strength++;
    if (hasLetters && hasNumbers) strength++;
    if (hasSpecial) strength++;

    if (strength === 1) return 'Weak';
    if (strength === 2) return 'Medium';
    if (strength === 3) return 'Strong';
    return 'Weak';
  }

  toggleVisibility(field: 'current' | 'new' | 'confirm') {
    switch(field) {
      case 'current': this.showCurrent = !this.showCurrent; break;
      case 'new': this.showNew = !this.showNew; break;
      case 'confirm': this.showConfirm = !this.showConfirm; break;
    }
  }

  onSubmit() {
    if (this.passwordForm.invalid) return;

    this.isLoading = true;
    this.successMessage = '';
    this.errorMessage = '';

    const payload = this.passwordForm.value;

    this.changePasswordService.updatePassword(payload).subscribe({
      next: (res) => {
        this.isLoading = false;
        this.successMessage = res.message;
        this.passwordForm.reset();
        
        // Hide success message automatically after 5 seconds
        setTimeout(() => {
            this.successMessage = '';
        }, 5000);
      },
      error: (err) => {
        this.isLoading = false;
        this.errorMessage = err.message || 'Current password is incorrect';
      }
    });
  }

  cancel() {
    this.passwordForm.reset();
    this.successMessage = '';
    this.errorMessage = '';
  }
}
