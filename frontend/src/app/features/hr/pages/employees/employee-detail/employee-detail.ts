import { ChangeDetectionStrategy, Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { EmployeeDetailView, EmployeePayload } from '../../../../../core/models/employee.model';
import { EmployeeService } from '../../../../../core/services/employee.service';
import { CustomSelectComponent } from '../../../../../shared/components/custom-select/custom-select';

@Component({
  selector: 'app-employee-detail',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterModule, CustomSelectComponent],
  templateUrl: './employee-detail.html',
  styleUrl: './employee-detail.css',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class EmployeeDetailComponent implements OnInit {
  employeeDetail$ = new BehaviorSubject<EmployeeDetailView | null>(null);
  isEditing$ = new BehaviorSubject<boolean>(false);
  saveMessage$ = new BehaviorSubject<string>('');
  form;

  departmentOptions = [
    { label: 'Engineering', value: 'Engineering' },
    { label: 'Human Resources', value: 'Human Resources' },
    { label: 'Finance', value: 'Finance' }
  ];

  employeeTypeOptions = [
    { label: 'Full-Time', value: 'Full-Time' },
    { label: 'Contract', value: 'Contract' },
    { label: 'Intern', value: 'Intern' }
  ];

  shiftOptions = [
    { label: 'General Shift', value: 'General Shift' },
    { label: 'Night Shift', value: 'Night Shift' }
  ];

  constructor(
    private readonly route: ActivatedRoute,
    private readonly fb: FormBuilder,
    private readonly employeeService: EmployeeService
  ) {
    this.form = this.fb.group({
      firstName: ['', Validators.required],
      lastName: ['', Validators.required],
      gender: [''],
      dob: [''],
      maritalStatus: [''],
      bloodGroup: [''],
      employeeType: [''],
      department: ['', Validators.required],
      designation: ['', Validators.required],
      workLocation: [''],
      shiftType: [''],
      doj: [''],
      officialEmail: ['', [Validators.required, Validators.email]],
      personalEmail: [''],
      mobile: ['', Validators.required],
      alternateMobile: [''],
      emergencyContactName: [''],
      emergencyContactNumber: [''],
      loginEmail: ['', [Validators.required, Validators.email]]
    });
  }

  ngOnInit(): void {
    this.isEditing$.next(this.route.snapshot.queryParamMap.get('mode') === 'edit');
    this.loadEmployee();
  }

  toggleEdit(): void {
    this.isEditing$.next(!this.isEditing$.value);
  }

  saveChanges(): void {
    const current = this.employeeDetail$.value;
    if (!current || this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const raw = this.form.getRawValue();
    const payload: EmployeePayload = {
      accountAccess: {
        loginEmail: raw.loginEmail || current.loginEmail,
        role: 'employee'
      },
      personalInfo: {
        firstName: raw.firstName || '',
        lastName: raw.lastName || '',
        gender: raw.gender || '',
        dob: raw.dob || '',
        maritalStatus: raw.maritalStatus || '',
        bloodGroup: raw.bloodGroup || ''
      },
      employmentInfo: {
        employeeCode: current.employee.employeeCode,
        employeeType: raw.employeeType || '',
        department: raw.department || '',
        designation: raw.designation || '',
        workLocation: raw.workLocation || '',
        shiftType: raw.shiftType || '',
        doj: raw.doj || ''
      },
      contactInfo: {
        officialEmail: raw.officialEmail || '',
        personalEmail: raw.personalEmail || '',
        mobile: raw.mobile || '',
        alternateMobile: raw.alternateMobile || '',
        emergencyContactName: raw.emergencyContactName || '',
        emergencyContactNumber: raw.emergencyContactNumber || ''
      }
    };

    this.employeeService.updateEmployee(current.employee.id, payload).subscribe(result => {
      this.saveMessage$.next(result.message);
      this.isEditing$.next(false);
      this.loadEmployee();
      setTimeout(() => this.saveMessage$.next(''), 2200);
    });
  }

  private loadEmployee(): void {
    const employeeId = this.route.snapshot.paramMap.get('employeeId');
    if (!employeeId) {
      return;
    }

    this.employeeService.getEmployeeById(employeeId).subscribe(detail => {
      this.employeeDetail$.next(detail);
      if (!detail) {
        return;
      }

      this.form.patchValue({
        firstName: detail.employee.firstName,
        lastName: detail.employee.lastName,
        gender: detail.employee.gender,
        dob: detail.employee.dob,
        maritalStatus: detail.employee.maritalStatus,
        bloodGroup: detail.employee.bloodGroup,
        employeeType: detail.employee.employeeType,
        department: detail.employee.department,
        designation: detail.employee.designation,
        workLocation: detail.employee.workLocation,
        shiftType: detail.employee.shiftType,
        doj: detail.employee.doj,
        officialEmail: detail.employee.officialEmail,
        personalEmail: detail.employee.personalEmail,
        mobile: detail.employee.mobile,
        alternateMobile: detail.employee.alternateMobile,
        emergencyContactName: detail.employee.emergencyContactName,
        emergencyContactNumber: detail.employee.emergencyContactNumber,
        loginEmail: detail.loginEmail
      });
    });
  }
}
