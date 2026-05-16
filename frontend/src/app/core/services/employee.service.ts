import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';

import { Employee, EmployeeCredentials, EmployeeDetailView, EmployeePayload, PaginatedResult } from '../models/employee.model';

interface BackendEmployee {
  id: number;
  user_id: number;
  employee_code: string;
  first_name: string;
  last_name: string;
  gender?: string | null;
  dob?: string | null;
  marital_status?: string | null;
  blood_group?: string | null;
  department?: string | null;
  designation?: string | null;
  employee_type?: string | null;
  work_location?: string | null;
  shift_type?: string | null;
  doj?: string | null;
  official_email: string;
  personal_email?: string | null;
  mobile: string;
  alternate_mobile?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_number?: string | null;
  status: 'Active' | 'Inactive';
}

interface BackendEmployeePayload {
  first_name: string;
  last_name: string;
  gender?: string;
  dob?: string;
  marital_status?: string;
  blood_group?: string;
  department?: string;
  designation?: string;
  employee_type?: string;
  work_location?: string;
  shift_type?: string;
  doj?: string;
  official_email: string;
  personal_email?: string;
  mobile: string;
  alternate_mobile?: string;
  emergency_contact_name?: string;
  emergency_contact_number?: string;
  status: 'Active' | 'Inactive';
}

interface BackendEmployeeCredentials {
  employee_id: number;
  employee_code: string;
  employee_name: string;
  username: string;
  email: string;
  password: string | null;
  temporary_password_hint: string;
  status: 'Active' | 'Inactive';
}

@Injectable({ providedIn: 'root' })
export class EmployeeService {
  private readonly apiUrl = 'http://localhost:8000/api/v1/employees';

  constructor(private readonly http: HttpClient) {}

  getEmployees(page: number, limit: number, search: string, department: string, type: string, status: string): Observable<PaginatedResult<Employee>> {
    return this.http.get<BackendEmployee[]>(this.apiUrl).pipe(
      map(rows => rows.map(row => this.mapEmployee(row))),
      map(rows => this.filterEmployees(rows, search, department, type, status)),
      map(rows => {
        const startIndex = (page - 1) * limit;
        return {
          data: rows.slice(startIndex, startIndex + limit),
          total: rows.length
        };
      })
    );
  }

  getEmployeeById(employeeId: string): Observable<EmployeeDetailView | null> {
    const normalizedId = this.normalizeEmployeeId(employeeId);
    if (!normalizedId) {
      return throwError(() => new Error('Employee ID is required.'));
    }
    console.log('EmployeeService.getEmployeeById request:', normalizedId);

    return this.http.get<BackendEmployee>(`${this.apiUrl}/${normalizedId}`).pipe(
      map(row => {
        console.log('EmployeeService.getEmployeeById response:', row);
        if (!row || row.id == null) {
          throw new Error('Employee detail response was empty or invalid.');
        }
        const employee = this.mapEmployee(row);
        return {
          employee,
          managerName: 'Assigned HR Team',
          loginEmail: employee.officialEmail,
          temporaryPasswordHint: 'Temp password set during account creation'
        };
      }),
      catchError(error => {
        console.error('EmployeeService.getEmployeeById error:', error);
        return throwError(() => error);
      })
    );
  }

  getEmployeeCredentials(employeeId: string): Observable<EmployeeCredentials> {
    const normalizedId = this.normalizeEmployeeId(employeeId);
    if (!normalizedId) {
      return throwError(() => new Error('Employee ID is required.'));
    }
    console.log('EmployeeService.getEmployeeCredentials request:', normalizedId);

    return this.http.get<BackendEmployeeCredentials>(`${this.apiUrl}/${normalizedId}/credentials`).pipe(
      map(row => {
        console.log('EmployeeService.getEmployeeCredentials response:', row);
        if (!row || row.employee_id == null) {
          throw new Error('Credentials response was empty or invalid.');
        }

        return {
          employeeId: String(row.employee_id),
          employeeCode: row.employee_code || '',
          employeeName: row.employee_name || '',
          username: row.username || row.email || '',
          email: row.email || '',
          password: row.password || null,
          temporaryPasswordHint: row.temporary_password_hint || 'No password information available',
          status: row.status
        };
      }),
      catchError(error => {
        console.error('EmployeeService.getEmployeeCredentials error:', error);
        return throwError(() => error);
      })
    );
  }

  createEmployee(payload: EmployeePayload): Observable<{ success: boolean; message: string; employee: Employee }> {
    return this.http.post<BackendEmployee>(this.apiUrl, this.toBackendPayload(payload)).pipe(
      map(row => {
        const employee = this.mapEmployee(row);
        return {
          success: true,
          message: `${employee.name} created successfully. Login email: ${employee.officialEmail}`,
          employee
        };
      })
    );
  }

  updateEmployee(employeeId: string, payload: EmployeePayload): Observable<{ success: boolean; message: string }> {
    const normalizedId = this.normalizeEmployeeId(employeeId);
    if (!normalizedId) {
      return throwError(() => new Error('Employee ID is required.'));
    }
    console.log('EmployeeService.updateEmployee request:', normalizedId, payload);

    return this.http.put<BackendEmployee>(`${this.apiUrl}/${normalizedId}`, this.toBackendPayload(payload)).pipe(
      map(row => {
        console.log('EmployeeService.updateEmployee response:', row);
        return { success: true, message: 'Employee updated successfully' };
      }),
      catchError(error => {
        console.error('EmployeeService.updateEmployee error:', error);
        return throwError(() => error);
      })
    );
  }

  private normalizeEmployeeId(employeeId: string): string {
    return String(employeeId ?? '').trim();
  }

  private filterEmployees(rows: Employee[], search: string, department: string, type: string, status: string): Employee[] {
    return rows.filter(employee => {
      const searchValue = search.trim().toLowerCase();
      const matchesSearch = !searchValue
        || employee.name.toLowerCase().includes(searchValue)
        || employee.employeeCode.toLowerCase().includes(searchValue)
        || employee.department.toLowerCase().includes(searchValue)
        || employee.officialEmail.toLowerCase().includes(searchValue);

      const matchesDepartment = !department || employee.department === department;
      const matchesType = !type || employee.employeeType === type;
      const matchesStatus = !status || employee.status === status;

      return matchesSearch && matchesDepartment && matchesType && matchesStatus;
    });
  }

  private toBackendPayload(payload: EmployeePayload): BackendEmployeePayload {
    return {
      first_name: payload.personalInfo.firstName,
      last_name: payload.personalInfo.lastName,
      gender: payload.personalInfo.gender || undefined,
      dob: payload.personalInfo.dob || undefined,
      marital_status: payload.personalInfo.maritalStatus || undefined,
      blood_group: payload.personalInfo.bloodGroup || undefined,
      department: payload.employmentInfo.department || undefined,
      designation: payload.employmentInfo.designation || undefined,
      employee_type: payload.employmentInfo.employeeType || undefined,
      work_location: payload.employmentInfo.workLocation || undefined,
      shift_type: payload.employmentInfo.shiftType || undefined,
      doj: payload.employmentInfo.doj || undefined,
      official_email: payload.contactInfo.officialEmail,
      personal_email: payload.contactInfo.personalEmail || undefined,
      mobile: payload.contactInfo.mobile,
      alternate_mobile: payload.contactInfo.alternateMobile || undefined,
      emergency_contact_name: payload.contactInfo.emergencyContactName || undefined,
      emergency_contact_number: payload.contactInfo.emergencyContactNumber || undefined,
      status: 'Active'
    };
  }

  private mapEmployee(row: BackendEmployee): Employee {
    return {
      id: String(row.id),
      userId: String(row.user_id),
      employeeCode: row.employee_code,
      name: `${row.first_name} ${row.last_name}`.trim(),
      firstName: row.first_name,
      lastName: row.last_name,
      department: row.department || '',
      designation: row.designation || '',
      employeeType: row.employee_type || '',
      status: row.status,
      login: row.status === 'Active' ? 'Enabled' : 'Disabled',
      officialEmail: row.official_email,
      personalEmail: row.personal_email || '',
      mobile: row.mobile,
      alternateMobile: row.alternate_mobile || '',
      emergencyContactName: row.emergency_contact_name || '',
      emergencyContactNumber: row.emergency_contact_number || '',
      gender: row.gender || '',
      dob: row.dob || '',
      maritalStatus: row.marital_status || '',
      bloodGroup: row.blood_group || '',
      workLocation: row.work_location || '',
      shiftType: row.shift_type || '',
      doj: row.doj || ''
    };
  }
}
