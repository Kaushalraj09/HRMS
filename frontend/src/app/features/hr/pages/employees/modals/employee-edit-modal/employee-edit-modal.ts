import { Component, EventEmitter, Input, OnInit, OnDestroy, Output, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators, AbstractControl, ValidationErrors } from '@angular/forms';
import { EmployeeService } from '../../../../../../core/services/employee.service';
import { MasterDataService } from '../../../../../../core/services/master-data.service';
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
  saveError = '';

  // Dropdown mappings
  genderOptions = [{ label: 'Male', value: 'Male' }, { label: 'Female', value: 'Female' }, { label: 'Other', value: 'Other' }];
  maritalOptions = [{ label: 'Single', value: 'Single' }, { label: 'Married', value: 'Married' }];
  bloodOptions = [
    { label: 'A+', value: 'A+' }, { label: 'A-', value: 'A-' },
    { label: 'B+', value: 'B+' }, { label: 'B-', value: 'B-' },
    { label: 'AB+', value: 'AB+' }, { label: 'AB-', value: 'AB-' },
    { label: 'O+', value: 'O+' }, { label: 'O-', value: 'O-' }
  ];
  empTypeOptions = [{ label: 'Full-Time', value: 'Full-Time' }, { label: 'Contract', value: 'Contract' }, { label: 'Intern', value: 'Intern' }];
  shiftOptions = [{ label: 'General Shift', value: 'General Shift' }, { label: 'Night Shift', value: 'Night Shift' }];
  departmentOptions = [{ label: 'Engineering', value: 'Engineering' }, { label: 'Human Resources', value: 'Human Resources' }, { label: 'Finance', value: 'Finance' }];
  designationOptions = [{ label: 'Software Engineer', value: 'Software Engineer' }, { label: 'QA Engineer', value: 'QA Engineer' }];
  locationOptions = [{ label: 'Main Office', value: 'Main Office' }, { label: 'Remote', value: 'Remote' }];
  roleOptions = [{ label: 'Employee', value: 'employee' }];
  managerOptions: Array<{ label: string; value: string | null }> = [{ label: 'No reporting manager', value: null }];

  private subscription?: Subscription;
  private managerSubscription?: Subscription;
  private masterDataSubscription?: Subscription;

  constructor(
    private fb: FormBuilder,
    private employeeService: EmployeeService,
    private masterDataService: MasterDataService,
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
        shiftId: [null],
        doj: [{ value: '', disabled: true }],
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

  isInvalid(group: string, field: string): boolean {
    const control = this.form.get(group)?.get(field);
    return !!(control && control.invalid && (control.dirty || control.touched));
  }

  get personalInfo() { return this.form.get('personalInfo') as FormGroup; }

  ngOnInit(): void {
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
    this.saveError = '';
    this.loadManagerOptions(employeeId);
    this.loadMasterData();

    this.subscription = this.employeeService.getEmployeeById(employeeId)
      .pipe(
        finalize(() => {
          this.isLoading = false;
          this.cdr.markForCheck();
        })
      )
      .subscribe({
        next: (detail) => {
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
                  shiftId: detail.employee.shiftId || null,
                  doj: detail.employee.doj || '',
                  reportingManagerId: detail.employee.reportingManagerId || null
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
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
    if (this.managerSubscription) {
      this.managerSubscription.unsubscribe();
    }
    if (this.masterDataSubscription) {
      this.masterDataSubscription.unsubscribe();
    }
  }

  private loadMasterData(): void {
    this.masterDataSubscription = this.masterDataService.getBootstrapData().subscribe({
      next: (res) => {
        if (res.departments && res.departments.length > 0) {
          this.departmentOptions = res.departments.map(d => ({ label: d.name, value: d.name }));
        }
        if (res.designations && res.designations.length > 0) {
          this.designationOptions = res.designations.map(d => ({ label: d.name, value: d.name }));
        }
        if (res.shifts && res.shifts.length > 0) {
          this.shiftOptions = res.shifts.map(s => ({ 
            label: `${s.name} (${s.start_time} - ${s.end_time})`, 
            value: s.id as any 
          }));
        }
        if (res.workLocations && res.workLocations.length > 0) {
          this.locationOptions = res.workLocations.map(l => ({ label: l.name, value: l.name }));
        }
        this.cdr.markForCheck();
      },
      error: (err) => console.warn('Failed to load master data for employee edit modal:', err)
    });
  }

  private loadManagerOptions(currentEmployeeId: string): void {
    this.managerSubscription = this.employeeService.getEmployees(1, 100, '', '', '', 'Active')
      .subscribe({
        next: (result) => {
          this.managerOptions = [
            { label: 'No reporting manager', value: null },
            ...result.data
              .filter(employee => employee.id !== currentEmployeeId)
              .map(employee => ({
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
    this.saveError = '';

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
        shiftType: raw.employmentInfo.shiftType, shiftId: raw.employmentInfo.shiftId, doj: raw.employmentInfo.doj, reportingManagerId: raw.employmentInfo.reportingManagerId
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
          this.saveError = err?.error?.detail || 'Failed to update employee';
          this.cdr.markForCheck();
        }
      });
  }

  close(): void {
    this.closed.emit(false);
  }
}
