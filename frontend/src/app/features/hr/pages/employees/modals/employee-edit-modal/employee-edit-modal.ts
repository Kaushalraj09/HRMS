import { Component, EventEmitter, Input, OnInit, OnDestroy, Output, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { EmployeeService } from '../../../../../../core/services/employee.service';
import { EmployeeDetailView, EmployeePayload } from '../../../../../../core/models/employee.model';
import { finalize } from 'rxjs/operators';
import { Subscription } from 'rxjs';
import { CustomSelectComponent } from '../../../../../../shared/components/custom-select/custom-select';

function pastDateValidator(control: AbstractControl): ValidationErrors | null {
  if (!control.value) return null;
  const selectedDate = new Date(control.value);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return selectedDate >= today ? { futureDate: true } : null;
}

@Component({
  selector: 'app-employee-edit-modal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, CustomSelectComponent],
  templateUrl: './employee-edit-modal.html',
  styleUrls: ['./employee-edit-modal.css']
})
export class EmployeeEditModalComponent implements OnInit, OnDestroy {
  @Input() employeeId!: string;
  @Output() closed = new EventEmitter<boolean>();

  form: FormGroup;
  employeeDetail: EmployeeDetailView | null = null;
  isLoading = true;
  isSaving = false;
  errorMessage = '';

  // Dropdown mappings
  genderOptions = [{ label: 'Male', value: 'Male' }, { label: 'Female', value: 'Female' }, { label: 'Other', value: 'Other' }];
  maritalOptions = [{ label: 'Single', value: 'Single' }, { label: 'Married', value: 'Married' }];
  bloodOptions = [{ label: 'A+', value: 'A+' }, { label: 'B+', value: 'B+' }, { label: 'O+', value: 'O+' }, { label: 'AB+', value: 'AB+' }];
  empTypeOptions = [{ label: 'Full-Time', value: 'Full-Time' }, { label: 'Contract', value: 'Contract' }, { label: 'Intern', value: 'Intern' }];
  shiftOptions = [{ label: 'General Shift', value: 'General Shift' }, { label: 'Night Shift', value: 'Night Shift' }];
  departmentOptions = [{ label: 'Engineering', value: 'Engineering' }, { label: 'Human Resources', value: 'Human Resources' }, { label: 'Finance', value: 'Finance' }];
  roleOptions = [{ label: 'Employee', value: 'employee' }];

  private subscription?: Subscription;

  constructor(
    private fb: FormBuilder,
    private employeeService: EmployeeService,
    private cdr: ChangeDetectorRef
  ) {
    this.form = this.fb.group({
      personalInfo: this.fb.group({
        firstName: [{ value: '', disabled: true }, Validators.required],
        lastName: [{ value: '', disabled: true }, Validators.required],
        gender: [{ value: '', disabled: true }],
        dob: [{ value: '', disabled: true }, [Validators.required, pastDateValidator]],
        maritalStatus: [''],
        bloodGroup: [{ value: '', disabled: true }]
      }),
      employmentInfo: this.fb.group({
        employeeType: [''],
        department: [''],
        designation: [''],
        workLocation: [''],
        shiftType: [''],
        doj: [{ value: '', disabled: true }]
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

  isInvalid(group: string, field: string): boolean {
    const control = this.form.get(group)?.get(field);
    return !!(control && control.invalid && (control.dirty || control.touched));
  }

  get personalInfo() { return this.form.get('personalInfo') as FormGroup; }

  ngOnInit(): void {
    console.log('EmployeeEditModal: Initializing for ID:', this.employeeId);
    const employeeId = String(this.employeeId ?? '').trim();
    if (!employeeId) {
      console.warn('EmployeeEditModal: No employeeId provided');
      this.isLoading = false;
      this.errorMessage = 'Employee ID is missing.';
      return;
    }
    if (!/^\d+$/.test(employeeId)) {
      console.warn('EmployeeEditModal: Invalid employeeId provided:', employeeId);
      this.isLoading = false;
      this.errorMessage = 'Invalid employee ID.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.subscription = this.employeeService.getEmployeeById(employeeId)
      .pipe(
        finalize(() => {
          console.log('EmployeeEditModal: Load finished for ID:', employeeId);
          this.isLoading = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (detail) => {
          console.log('EmployeeEditModal: Data received:', detail);
          if (detail && detail.employee) {
            this.employeeDetail = detail;
            try {
              this.form.patchValue({
                personalInfo: {
                  firstName: detail.employee.firstName || '',
                  lastName: detail.employee.lastName || '',
                  gender: detail.employee.gender || '',
                  dob: detail.employee.dob || '',
                  maritalStatus: detail.employee.maritalStatus || '',
                  bloodGroup: detail.employee.bloodGroup || ''
                },
                employmentInfo: {
                  employeeType: detail.employee.employeeType || '',
                  department: detail.employee.department || '',
                  designation: detail.employee.designation || '',
                  workLocation: detail.employee.workLocation || '',
                  shiftType: detail.employee.shiftType || '',
                  doj: detail.employee.doj || ''
                },
                contactInfo: {
                  officialEmail: detail.employee.officialEmail || '',
                  personalEmail: detail.employee.personalEmail || '',
                  mobile: detail.employee.mobile || '',
                  alternateMobile: detail.employee.alternateMobile || '',
                  emergencyContactName: detail.employee.emergencyContactName || '',
                  emergencyContactNumber: detail.employee.emergencyContactNumber || ''
                }
              });
            } catch (patchErr) {
              console.error('EmployeeEditModal: Error patching form:', patchErr);
              this.errorMessage = 'Error loading form data.';
            }
          } else {
            this.errorMessage = 'Employee details not found or invalid format.';
          }
          this.cdr.markForCheck();
        },
        error: (err) => {
          console.error('EmployeeEditModal: Error loading data:', err);
          this.errorMessage = err?.error?.detail || err?.message || 'Could not load employee data. Please try again.';
          this.cdr.markForCheck();
        }
      });
  }

  ngOnDestroy(): void {
    console.log('EmployeeEditModal: Component being destroyed for ID:', this.employeeId);
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
  }

  save(): void {
    if (this.form.invalid || !this.employeeDetail) return;

    const employeeId = String(this.employeeId ?? '').trim();
    if (!employeeId) {
      this.errorMessage = 'Employee ID is missing.';
      return;
    }
    if (!/^\d+$/.test(employeeId)) {
      this.errorMessage = 'Invalid employee ID.';
      return;
    }

    this.isSaving = true;
    this.errorMessage = '';

    const raw = this.form.getRawValue();
    const payload: EmployeePayload = {
      accountAccess: { loginEmail: raw.contactInfo.officialEmail, role: 'employee' },
      personalInfo: {
        firstName: raw.personalInfo.firstName, lastName: raw.personalInfo.lastName, gender: raw.personalInfo.gender, dob: raw.personalInfo.dob,
        maritalStatus: raw.personalInfo.maritalStatus, bloodGroup: raw.personalInfo.bloodGroup
      },
      employmentInfo: {
        employeeCode: this.employeeDetail.employee.employeeCode, employeeType: raw.employmentInfo.employeeType,
        department: raw.employmentInfo.department, designation: raw.employmentInfo.designation, workLocation: raw.employmentInfo.workLocation,
        shiftType: raw.employmentInfo.shiftType, doj: raw.employmentInfo.doj
      },
      contactInfo: {
        officialEmail: raw.contactInfo.officialEmail, personalEmail: raw.contactInfo.personalEmail,
        mobile: raw.contactInfo.mobile, alternateMobile: raw.contactInfo.alternateMobile,
        emergencyContactName: raw.contactInfo.emergencyContactName, emergencyContactNumber: raw.contactInfo.emergencyContactNumber
      }
    };

    this.employeeService.updateEmployee(employeeId, payload)
      .pipe(finalize(() => {
        this.isSaving = false;
        this.cdr.markForCheck();
      }))
      .subscribe({
        next: () => this.closed.emit(true),
        error: (err) => {
          this.errorMessage = err?.error?.detail || 'Failed to update employee';
          this.cdr.markForCheck();
        }
      });
  }

  close(): void {
    this.closed.emit(false);
  }
}
