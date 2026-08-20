import { Component, EventEmitter, OnInit, Output, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { HrService } from '../../../../../../core/services/hr.service';
import { MasterDataService } from '../../../../../../core/services/master-data.service';
import { CreateHrPayload } from '../../../../../../core/models/hr.model';
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
  selector: 'app-hr-add-modal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, CustomSelectComponent],
  templateUrl: './hr-add-modal.html',
  styleUrls: ['./hr-add-modal.css']
})
export class HrAddModalComponent implements OnInit {
  @Output() closed = new EventEmitter<boolean>();
  
  form: FormGroup;
  isSaving = false;
  errorMessage = '';
  successMessage = '';

  // Dropdown mappings
  genderOptions = [{label: 'Male', value: 'Male'}, {label: 'Female', value: 'Female'}, {label: 'Other', value: 'Other'}];
  maritalOptions = [{label: 'Single', value: 'Single'}, {label: 'Married', value: 'Married'}];
  bloodOptions = [
    {label: 'A+', value: 'A+'}, {label: 'A-', value: 'A-'},
    {label: 'B+', value: 'B+'}, {label: 'B-', value: 'B-'},
    {label: 'AB+', value: 'AB+'}, {label: 'AB-', value: 'AB-'},
    {label: 'O+', value: 'O+'}, {label: 'O-', value: 'O-'}
  ];
  empTypeOptions = [{label: 'Full-Time', value: 'Full-Time'}, {label: 'Contract', value: 'Contract'}, {label: 'Intern', value: 'Intern'}];
  shiftOptions = [{label: 'General Shift', value: 'General Shift'}, {label: 'Night Shift', value: 'Night Shift'}];
  departmentOptions = [
    { label: 'Human Resources', value: 'Human Resources' },
    { label: 'Operations', value: 'Operations' },
    { label: 'People Success', value: 'People Success' }
  ];
  designationOptions = [{ label: 'HR Manager', value: 'HR Manager' }, { label: 'HR Specialist', value: 'HR Specialist' }];
  locationOptions = [{ label: 'Main Office', value: 'Main Office' }, { label: 'Remote', value: 'Remote' }];
  roleOptions = [{label: 'HR', value: 'hr'}];

  constructor(
    private fb: FormBuilder,
    private hrService: HrService,
    private masterDataService: MasterDataService,
    private cdr: ChangeDetectorRef
  ) {
    this.form = this.fb.group({
      accountAccess: this.fb.group({
        loginEmail: ['', [Validators.required, Validators.email]],
        role: ['hr', Validators.required]
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
        employeeType: ['Full-Time'],
        department: ['Human Resources'],
        designation: ['HR Manager'],
        workLocation: ['Main Office'],
        shiftType: ['General Shift'],
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

    // Auto-sync Login Email and Official / Company Email
    const loginEmailCtrl = this.form.get('accountAccess.loginEmail');
    const officialEmailCtrl = this.form.get('contactInfo.officialEmail');

    if (loginEmailCtrl && officialEmailCtrl) {
      loginEmailCtrl.valueChanges.subscribe(val => {
        if (officialEmailCtrl.value !== val) {
          officialEmailCtrl.setValue(val, { emitEvent: false });
          if (loginEmailCtrl.touched) {
            officialEmailCtrl.markAsTouched();
          }
          officialEmailCtrl.updateValueAndValidity({ emitEvent: false });
        }
      });

      officialEmailCtrl.valueChanges.subscribe(val => {
        if (loginEmailCtrl.value !== val) {
          loginEmailCtrl.setValue(val, { emitEvent: false });
          if (officialEmailCtrl.touched) {
            loginEmailCtrl.markAsTouched();
          }
          loginEmailCtrl.updateValueAndValidity({ emitEvent: false });
        }
      });
    }
  }

  ngOnInit(): void {
    this.masterDataService.getBootstrapData().subscribe({
      next: (res) => {
        if (res.departments && res.departments.length > 0) {
          this.departmentOptions = res.departments.map(d => ({ label: d.name, value: d.name }));
        }
        if (res.designations && res.designations.length > 0) {
          this.designationOptions = res.designations.map(d => ({ label: d.name, value: d.name }));
        }
        if (res.shifts && res.shifts.length > 0) {
          this.shiftOptions = res.shifts.map(s => ({ label: s.name, value: s.name }));
        }
        if (res.workLocations && res.workLocations.length > 0) {
          this.locationOptions = res.workLocations.map(l => ({ label: l.name, value: l.name }));
        }
        this.cdr.markForCheck();
      },
      error: (err) => console.warn('Failed to load master data for HR modal:', err)
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

    const formValue = this.form.getRawValue();
    
    // Map full detailed structure to CreateHrPayload
    const payload: CreateHrPayload = {
      fullName: `${formValue.personalInfo.firstName} ${formValue.personalInfo.lastName}`.trim(),
      email: formValue.accountAccess.loginEmail || formValue.contactInfo.officialEmail,
      phone: formValue.contactInfo.mobile,
      designation: formValue.employmentInfo.designation || 'HR',
      department: formValue.employmentInfo.department || 'Human Resources',
      status: 'Active'
    };

    this.hrService.createHr(payload)
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
          this.errorMessage = err?.error?.detail || 'Failed to create HR user';
          this.cdr.markForCheck();
        }
      });
  }

  close(): void {
    this.closed.emit(false);
  }
}
