import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';

import { buildApiUrl } from '../config/api.config';
import { Employee, EmployeeCodeHistory, EmployeeCredentials, EmployeeDetailView, EmployeePayload, PaginatedResult } from '../models/employee.model';

interface BackendEmployee {
  id: number;
  user_id: number;
  reporting_manager_id?: number | null;
  reporting_manager_name?: string | null;
  employee_code: string;
  legacy_employee_code?: string | null;
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
  shift_id?: number | null;
  shift?: { id: number, name: string, code: string } | null;
  doj?: string | null;
  official_email: string;
  personal_email?: string | null;
  mobile: string;
  alternate_mobile?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_number?: string | null;
  status: 'Active' | 'Inactive';
  bank_name?: string | null;
  bank_account_no?: string | null;
  ifsc_code?: string | null;
  micr_code?: string | null;
  pan_number?: string | null;
  uan_number?: string | null;
  pf_number?: string | null;
  user_role?: string | null;
  is_manager?: boolean | null;
  direct_reports_count?: number | null;
}

interface BackendEmployeeStats {
  total: number;
  active: number;
  on_leave: number;
  inactive: number;
}

interface BackendPaginatedEmployees {
  data: BackendEmployee[];
  total: number;
  stats?: BackendEmployeeStats;
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
  shift_id?: number | null;
  doj?: string;
  official_email: string;
  personal_email?: string;
  mobile: string;
  alternate_mobile?: string;
  emergency_contact_name?: string;
  emergency_contact_number?: string;
  reporting_manager_id?: number | null;
  status: 'Active' | 'Inactive';
  bank_name?: string;
  bank_account_no?: string;
  ifsc_code?: string;
  micr_code?: string;
  pan_number?: string;
  uan_number?: string;
  pf_number?: string;
  role?: string;
  employee_code?: string;
  legacy_employee_code?: string;
}

interface BackendEmployeeCredentials {
  employee_id: number;
  employee_code: string;
  employee_name: string;
  username: string;
  email: string;
  activation_required?: boolean;
  temporary_password_hint: string;
  status: 'Active' | 'Inactive';
}

@Injectable({ providedIn: 'root' })
export class EmployeeService {
  private readonly apiUrl = buildApiUrl('/employees');

  constructor(private readonly http: HttpClient) {}

  getEmployees(
    page: number, 
    limit: number, 
    search: string, 
    department: string, 
    type: string, 
    status: string,
    excludeHr: boolean = false
  ): Observable<PaginatedResult<Employee>> {
    const params = {
      page,
      limit,
      search: search.trim(),
      department,
      type,
      status,
      exclude_hr: excludeHr
    };

    return this.http.get<BackendPaginatedEmployees>(this.apiUrl, { params }).pipe(
      map(result => ({
        data: result.data.map(row => this.mapEmployee(row)),
        total: result.total,
        stats: result.stats ? {
          total: result.stats.total,
          active: result.stats.active,
          onLeave: result.stats.on_leave,
          inactive: result.stats.inactive
        } : undefined
      }))
    );
  }

  getEmployeeById(employeeId: string): Observable<EmployeeDetailView | null> {
    const normalizedId = this.normalizeEmployeeId(employeeId);
    if (!normalizedId) {
      return throwError(() => new Error('Employee ID is required.'));
    }
    return this.http.get<BackendEmployee>(`${this.apiUrl}/${normalizedId}`).pipe(
      map(row => {
        if (!row || row.id == null) {
          throw new Error('Employee detail response was empty or invalid.');
        }
        const employee = this.mapEmployee(row);
        return {
          employee,
          managerName: row.reporting_manager_name || 'Assigned HR Team',
          loginEmail: employee.officialEmail,
          temporaryPasswordHint: 'Use the password setup email to activate this account.'
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
    return this.http.get<BackendEmployeeCredentials>(`${this.apiUrl}/${normalizedId}/credentials`).pipe(
      map(row => {
        if (!row || row.employee_id == null) {
          throw new Error('Credentials response was empty or invalid.');
        }

        return {
          employeeId: String(row.employee_id),
          employeeCode: row.employee_code || '',
          employeeName: row.employee_name || '',
          username: row.username || row.email || '',
          email: row.email || '',
          activationRequired: row.activation_required ?? true,
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
          message: `${employee.name} created successfully. Password setup email has been sent.`,
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
    return this.http.put<BackendEmployee>(`${this.apiUrl}/${normalizedId}`, this.toBackendPayload(payload)).pipe(
      map(row => {
        return { success: true, message: 'Employee updated successfully' };
      }),
      catchError(error => {
        console.error('EmployeeService.updateEmployee error:', error);
        return throwError(() => error);
      })
    );
  }

  deleteEmployee(employeeId: string): Observable<{ success: boolean; message: string }> {
    const normalizedId = this.normalizeEmployeeId(employeeId);
    if (!normalizedId) {
      return throwError(() => new Error('Employee ID is required.'));
    }
    return this.http.delete<{ success: boolean; message: string }>(`${this.apiUrl}/${normalizedId}`).pipe(
      map(row => {
        return row;
      }),
      catchError(error => {
        console.error('EmployeeService.deleteEmployee error:', error);
        return throwError(() => error);
      })
    );
  }

  assignManagerRole(employeeId: string): Observable<Employee> {
    return this.http.post<BackendEmployee>(`${this.apiUrl}/${this.normalizeEmployeeId(employeeId)}/assign-manager`, {}).pipe(
      map(row => this.mapEmployee(row))
    );
  }

  revokeManagerRole(employeeId: string): Observable<Employee> {
    return this.http.post<BackendEmployee>(`${this.apiUrl}/${this.normalizeEmployeeId(employeeId)}/revoke-manager`, {}).pipe(
      map(row => this.mapEmployee(row))
    );
  }

  getAllManagers(): Observable<Employee[]> {
    return this.http.get<BackendEmployee[]>(`${this.apiUrl}/managers/all`).pipe(
      map(rows => rows.map(r => this.mapEmployee(r)))
    );
  }

  assignTeam(managerEmployeeId: string, employeeIds: number[]): Observable<Employee[]> {
    return this.http.post<BackendEmployee[]>(`${this.apiUrl}/${this.normalizeEmployeeId(managerEmployeeId)}/assign-team`, {
      employee_ids: employeeIds
    }).pipe(
      map(rows => rows.map(r => this.mapEmployee(r)))
    );
  }

  getManagerTeam(managerEmployeeId: string): Observable<Employee[]> {
    return this.http.get<BackendEmployee[]>(`${this.apiUrl}/${this.normalizeEmployeeId(managerEmployeeId)}/team`).pipe(
      map(rows => rows.map(r => this.mapEmployee(r)))
    );
  }

  changeEmployeeCode(employeeId: string, newCode: string, reason: string): Observable<{ success: boolean; message: string; employee: Employee }> {
    const normalizedId = this.normalizeEmployeeId(employeeId);
    if (!normalizedId) {
      return throwError(() => new Error('Employee ID is required.'));
    }
    return this.http.post<BackendEmployee>(`${this.apiUrl}/${normalizedId}/change-code`, {
      new_employee_code: newCode,
      reason: reason
    }).pipe(
      map(row => {
        const employee = this.mapEmployee(row);
        return {
          success: true,
          message: `Employee code updated to ${employee.employeeCode} successfully.`,
          employee
        };
      })
    );
  }

  migrateEmployeeToAivanCode(employeeId: string, customCode?: string, reason?: string): Observable<{ success: boolean; message: string; employee: Employee }> {
    const normalizedId = this.normalizeEmployeeId(employeeId);
    if (!normalizedId) {
      return throwError(() => new Error('Employee ID is required.'));
    }
    return this.http.post<BackendEmployee>(`${this.apiUrl}/${normalizedId}/migrate-to-aivan-code`, {
      new_employee_code: customCode ? customCode.trim() : null,
      reason: reason ? reason.trim() : 'Standardized to official AIVAN series'
    }).pipe(
      map(row => {
        const employee = this.mapEmployee(row);
        return {
          success: true,
          message: `Employee code updated to ${employee.employeeCode} successfully.`,
          employee
        };
      })
    );
  }

  getEmployeeCodeHistory(employeeId: string): Observable<EmployeeCodeHistory[]> {
    const normalizedId = this.normalizeEmployeeId(employeeId);
    if (!normalizedId) {
      return throwError(() => new Error('Employee ID is required.'));
    }
    return this.http.get<EmployeeCodeHistory[]>(`${this.apiUrl}/${normalizedId}/code-history`);
  }

  getNextEmployeeCode(prefix: string = 'AIVAN'): Observable<{ prefix: string; nextNumber: number; nextCode: string }> {
    return this.http.get<{ prefix: string; nextNumber: number; nextCode: string }>(`${this.apiUrl}/next-code`, {
      params: { prefix }
    });
  }

  private normalizeEmployeeId(employeeId: string): string {
    return String(employeeId ?? '').trim();
  }

  private toBackendPayload(payload: EmployeePayload): BackendEmployeePayload {
    return {
      role: payload.accountAccess?.role || undefined,
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
      shift_id: payload.employmentInfo.shiftId ? Number(payload.employmentInfo.shiftId) : undefined,
      doj: payload.employmentInfo.doj || undefined,
      reporting_manager_id: payload.employmentInfo.reportingManagerId ? Number(payload.employmentInfo.reportingManagerId) : null,
      official_email: payload.contactInfo.officialEmail,
      personal_email: payload.contactInfo.personalEmail || undefined,
      mobile: payload.contactInfo.mobile,
      alternate_mobile: payload.contactInfo.alternateMobile || undefined,
      emergency_contact_name: payload.contactInfo.emergencyContactName || undefined,
      emergency_contact_number: payload.contactInfo.emergencyContactNumber || undefined,
      status: 'Active',
      bank_name: payload.statutoryInfo?.bankName || undefined,
      bank_account_no: payload.statutoryInfo?.bankAccountNo || undefined,
      ifsc_code: payload.statutoryInfo?.ifscCode || undefined,
      micr_code: payload.statutoryInfo?.micrCode || undefined,
      pan_number: payload.statutoryInfo?.panNumber || undefined,
      uan_number: payload.statutoryInfo?.uanNumber || undefined,
      pf_number: payload.statutoryInfo?.pfNumber || undefined,
      employee_code: payload.employmentInfo.employeeCode?.trim() || undefined,
      legacy_employee_code: payload.employmentInfo.legacyEmployeeCode?.trim() || undefined
    };
  }

  private mapEmployee(row: BackendEmployee): Employee {
    const firstName = (row.first_name || '').trim();
    const lastName = (row.last_name || '').trim();
    const fullName = `${firstName} ${lastName}`.trim();
    return {
      id: String(row.id),
      userId: String(row.user_id),
      reportingManagerId: row.reporting_manager_id != null ? String(row.reporting_manager_id) : null,
      reportingManagerName: row.reporting_manager_name || null,
      employeeCode: row.employee_code,
      legacyEmployeeCode: row.legacy_employee_code || null,
      employeeCodeSource: (row as any).employee_code_source || 'AIVAN_GENERATED',
      employeeCodeStatus: (row as any).employee_code_status || 'ACTIVE',
      name: fullName || 'Employee',
      firstName: firstName,
      lastName: lastName,
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
      shiftId: row.shift_id ?? null,
      shift: row.shift || null,
      doj: row.doj || '',
      bankName: row.bank_name || '',
      bankAccountNo: row.bank_account_no || '',
      ifscCode: row.ifsc_code || '',
      micrCode: row.micr_code || '',
      panNumber: row.pan_number || '',
      uanNumber: row.uan_number || '',
      pfNumber: row.pf_number || '',
      userRole: row.user_role || 'Employee',
      isManager: row.is_manager ?? (row.user_role?.toLowerCase() === 'manager'),
      directReportsCount: row.direct_reports_count ?? 0
    };
  }
}
