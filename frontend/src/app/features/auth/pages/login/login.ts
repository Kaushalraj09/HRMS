import { ChangeDetectorRef, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrls: ['./login.css'],
})
export class Login {
  loginForm: FormGroup;
  message: string = '';
  messageType: 'success' | 'error' | '' = 'success';
  showPopup: boolean = false;
  timeoutRef: any;

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
        this.message = 'Login successful';
        this.messageType = 'success';
        this.showPopup = true;

        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          this.router.navigate([this.authService.getLandingRoute(response.me.role)]);
        }, 900);
      },
      error: (error) => {
        this.message = error.message || 'Invalid email or password';
        this.messageType = 'error';
        this.showPopup = true;

        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          this.cdr.detectChanges();
        }, 1600);
      }
    });
  }

  // closePopup() {
  //   this.showPopup = false;
  //   if (this.timeoutRef) {
  //     clearTimeout(this.timeoutRef);
  //   }
  // }

  get f() {
    return this.loginForm.controls;
  }
}
