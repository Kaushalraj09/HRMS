import { ChangeDetectorRef, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, Validators, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

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
    timeoutRef: any;
  
    constructor(private fb: FormBuilder, private router: Router, private cdr: ChangeDetectorRef) {
      this.forgotPasswordForm = this.fb.group({
        email: ['', [Validators.required, Validators.email]],
      });
    }
  
    onForgotPassword() {
      console.log("CLICKED");
  
      if (this.timeoutRef) {
        clearTimeout(this.timeoutRef);
      }
  
      if (this.forgotPasswordForm.invalid) {
        this.forgotPasswordForm.markAllAsTouched();
        return;
      }
  
      const { email } = this.forgotPasswordForm.value;
  
      if (email === 'kaushal@gmail.com') {
        this.message = 'Password reset link sent to your email ✅';
        this.messageType = 'success';
        this.showPopup = true;
  
        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          this.router.navigate(['/auth/login']);
        }, 1500);
      } else {
        this.message = 'Invalid email ❌';
        this.messageType = 'error';
        this.showPopup = true;
  
        this.timeoutRef = setTimeout(() => {
          this.showPopup = false;
          this.cdr.detectChanges();
        }, 1500);
      }
    }

  
    get f() {
      return this.forgotPasswordForm.controls;
    }
  }
  

