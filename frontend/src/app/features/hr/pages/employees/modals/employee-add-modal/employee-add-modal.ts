import { Component, EventEmitter, OnInit, Output, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { EmployeeService } from '../../../../../../core/services/employee.service';
import { EmployeePayload } from '../../../../../../core/models/employee.model';
import { CustomSelectComponent } from '../../../../../../shared/components/custom-select/custom-select';
import { finalize } from 'rxjs';

function pastDateValidator(control: AbstractControl): ValidationErrors | null {
  if (!control.value) return null;
  const selectedDate = new Date(control.value);
  const today = new Date();
  today.setHours(0,0,0,0);
  return selectedDate >= today ? { futureDate: true } : null;
}

@Component({
  selector: 'app-employee-add-modal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, CustomSelectComponent],
  templateUrl: './employee-add-modal.html',
  styleUrls: ['./employee-add-modal.css']
})
export class EmployeeAddModalComponent implements OnInit {
  @Output() closed = new EventEmitter<boolean>();
  
  form: FormGroup;
  isSaving = false;
  errorMessage = '';
  successMessage = '';

  // Dropdown mappings
  genderOptions = [{label: 'Male', value: 'Male'}, {label: 'Female', value: 'Female'}, {label: 'Other', value: 'Other'}];
  maritalOptions = [{label: 'Single', value: 'Single'}, {label: 'Married', value: 'Married'}];
  bloodOptions = [{label: 'A+', value: 'A+'}, {label: 'B+', value: 'B+'}, {label: 'O+', value: 'O+'}, {label: 'AB+', value: 'AB+'}];
  empTypeOptions = [{label: 'Full-Time', value: 'Full-Time'}, {label: 'Contract', value: 'Contract'}, {label: 'Intern', value: 'Intern'}];
  shiftOptions = [{label: 'General Shift', value: 'General Shift'}, {label: 'Night Shift', value: 'Night Shift'}];
  departmentOptions = [{label: 'Engineering', value: 'Engineering'}, {label: 'Human Resources', value: 'Human Resources'}, {label: 'Finance', value: 'Finance'}];
  roleOptions = [{label: 'Employee', value: 'employee'}];
  managerOptions: Array<{ label: string; value: string | null }> = [{ label: 'No reporting manager', value: null }];

  constructor(
    private fb: FormBuilder,
    private employeeService: EmployeeService,
    private cdr: ChangeDetectorRef
  ) {
    this.form = this.fb.group({
      accountAccess: this.fb.group({
        loginEmail: ['', [Validators.required, Validators.email]],
        role: ['employee', Validators.required]
      }),
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
        doj: [''],
        reportingManagerId: [null]
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

  ngOnInit(): void {
    this.employeeService.getEmployees(1, 100, '', '', '', 'Active')
      .subscribe({
        next: (result) => {
          this.managerOptions = [
            { label: 'No reporting manager', value: null },
            ...result.data.map(employee => ({
              label: `${employee.name} (${employee.employeeCode})`,
              value: employee.id
            }))
          ];
          this.cdr.markForCheck();
        },
        error: () => {
          this.managerOptions = [{ label: 'No reporting manager', value: null }];
          this.cdr.markForCheck();
        }
      });
  }

  isInvalid(group: string, field: string): boolean {
    const control = this.form.get(group)?.get(field);
    return !!(control && control.invalid && (control.dirty || control.touched));
  }

  get personalInfo() { return this.form.get('personalInfo') as FormGroup; }

  save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.isSaving = true;
    this.errorMessage = '';

    const payload = this.form.getRawValue() as EmployeePayload;
    
    // Default values matching backend requirements if not strictly provided
    if (!payload.employmentInfo.employeeCode) {
      payload.employmentInfo.employeeCode = 'NEW';
    }

    this.employeeService.createEmployee(payload)
      .pipe(finalize(() => {
        this.isSaving = false;
        this.cdr.markForCheck();
      }))
      .subscribe({
        next: (res) => {
          this.successMessage = res.message;
          this.cdr.markForCheck();
          setTimeout(() => this.closed.emit(true), 1500);
        },
        error: (err) => {
          this.errorMessage = err?.error?.detail || 'Failed to create employee';
          this.cdr.markForCheck();
        }
      });
  }

  close(): void {
    this.closed.emit(false);
  }
}
