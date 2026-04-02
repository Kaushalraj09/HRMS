import { ChangeDetectorRef, Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css'],
})
export class LoginComponent {
  loginForm: FormGroup;
  message: string = '';
  messageType: 'success' | 'error' | '' = 'success';
  showPopup: boolean = false;
  timeoutRef: any;

  constructor(private fb: FormBuilder, private router: Router, private cdr: ChangeDetectorRef) {
    this.loginForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      password: ['', [Validators.required, Validators.minLength(6)]],
    });
  }

  onLogin() {
    console.log("CLICKED");

    if (this.timeoutRef) {
      clearTimeout(this.timeoutRef);
    }

    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    const { email, password } = this.loginForm.value;

    if (email === 'kaushal@gmail.com' && password === '123456') {
      this.message = 'Login successful ✅';
      this.messageType = 'success';
      this.showPopup = true;

      this.timeoutRef = setTimeout(() => {
        this.showPopup = false;
        this.router.navigate(['/master-dashboard']);
      }, 1500);
    } else {
      this.message = 'Invalid email or password ❌';
      this.messageType = 'error';
      this.showPopup = true;

      this.timeoutRef = setTimeout(() => {
        this.showPopup = false;
        this.cdr.detectChanges();
      }, 1500);
    }
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
