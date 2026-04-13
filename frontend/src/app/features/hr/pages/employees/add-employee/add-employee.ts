import { Component, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl, ValidationErrors } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { CustomSelectComponent } from '../../../../../shared/components/custom-select/custom-select';
import { EmployeeService } from '../../../../../core/services/employee.service';

function pastDateValidator(control: AbstractControl): ValidationErrors | null {
  if (!control.value) return null;
  const selectedDate = new Date(control.value);
  const today = new Date();
  today.setHours(0,0,0,0);
  return selectedDate >= today ? { futureDate: true } : null;
}

@Component({
  selector: 'app-add-employee',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, CustomSelectComponent],
  templateUrl: './add-employee.html',
  styleUrl: './add-employee.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AddEmployeeComponent {
  employeeForm!: FormGroup;
  isSubmitting$ = new BehaviorSubject<boolean>(false);
  successMessage$ = new BehaviorSubject<string>('');

  // Dropdown mappings
  genderOptions = [{label: 'Male', value: 'Male'}, {label: 'Female', value: 'Female'}, {label: 'Other', value: 'Other'}];
  maritalOptions = [{label: 'Single', value: 'Single'}, {label: 'Married', value: 'Married'}];
  bloodOptions = [{label: 'A+', value: 'A+'}, {label: 'B+', value: 'B+'}, {label: 'O+', value: 'O+'}, {label: 'AB+', value: 'AB+'}];
  empTypeOptions = [{label: 'Full-Time', value: 'Full-Time'}, {label: 'Contract', value: 'Contract'}, {label: 'Intern', value: 'Intern'}];
  shiftOptions = [{label: 'General Shift', value: 'General Shift'}, {label: 'Night Shift', value: 'Night Shift'}];
  departmentOptions = [{label: 'Engineering', value: 'Engineering'}, {label: 'HR', value: 'HR'}, {label: 'Finance', value: 'Finance'}];

  constructor(private fb: FormBuilder, private employeeService: EmployeeService, private router: Router) {
    this.employeeForm = this.fb.group({
      personalInfo: this.fb.group({
        firstName: ['', Validators.required],
        lastName: ['', Validators.required],
        gender: [''],
        dob: ['', [Validators.required, pastDateValidator]],
        maritalStatus: [''],
        bloodGroup: ['']
      }),
      employmentInfo: this.fb.group({
        employeeType: [''],
        department: [''],
        designation: [''],
        workLocation: [''],
        shiftType: [''],
        doj: ['']
      }),
      contactInfo: this.fb.group({
        officialEmail: ['', [Validators.required, Validators.email]],
        personalEmail: ['', Validators.email],
        mobile: ['', [Validators.required, Validators.pattern('^[0-9]{10}$')]],
        alternateMobile: ['', Validators.pattern('^[0-9]{10}$')],
        emergencyContactName: [''],
        emergencyContactNumber: ['', Validators.pattern('^[0-9]{10}$')]
      })
    });
  }

  get personalInfo() { return this.employeeForm.get('personalInfo') as FormGroup; }
  get contactInfo() { return this.employeeForm.get('contactInfo') as FormGroup; }

  onSubmit() {
    if (this.employeeForm.invalid) {
      this.employeeForm.markAllAsTouched();
      return;
    }

    this.isSubmitting$.next(true);
    this.employeeService.createEmployee(this.employeeForm.value).subscribe(res => {
      this.isSubmitting$.next(false);
      if (res.success) {
        this.successMessage$.next(res.message);
        this.employeeForm.reset();
        setTimeout(() => this.successMessage$.next(''), 4000);
      }
    });
  }

  isInvalid(group: string, field: string): boolean {
    const control = this.employeeForm.get(group)?.get(field);
    return !!(control && control.invalid && (control.dirty || control.touched));
  }
}
