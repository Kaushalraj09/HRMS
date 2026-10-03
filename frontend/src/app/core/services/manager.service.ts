import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, map } from 'rxjs';
import { buildApiUrl } from '../config/api.config';
import { Employee, PaginatedResult } from '../models/employee.model';
import { TimeOffRequest } from '../models/timeoff.model';

export interface ManagerDashboardStats {
  totalEmployees: number;
  presentToday: number;
  absentToday: number;
  onLeaveToday: number;
  lateToday: number;
  currentlyWorking: number;
  pendingApprovals: number;
  teamOverview?: Array<{
    employeeId: number;
    employeeCode: string;
    name: string;
    department: string;
    designation: string;
    status: string;
    punchIn?: string | null;
    punchOut?: string | null;
  }>;
}

export interface AttendanceTrendData {
  period: string;
  labels: string[];
  present: number[];
  leave: number[];
  absent: number[];
}

@Injectable({
  providedIn: 'root'
})
export class ManagerService {
  private readonly apiUrl = buildApiUrl('/manager');

  constructor(private readonly http: HttpClient) {}

  private mapEmployee(row: any): Employee {
    const firstName = (row.first_name || row.firstName || '').trim();
    const lastName = (row.last_name || row.lastName || '').trim();
    const fullName = row.name || `${firstName} ${lastName}`.trim();
    return {
      id: String(row.id),
      userId: String(row.user_id || row.userId || ''),
      reportingManagerId: row.reporting_manager_id != null ? String(row.reporting_manager_id) : (row.reportingManagerId || null),
      reportingManagerName: row.reporting_manager_name || row.reportingManagerName || null,
      employeeCode: row.employee_code || row.employeeCode || '',
      legacyEmployeeCode: row.legacy_employee_code || row.legacyEmployeeCode || null,
      name: fullName || 'Employee',
      firstName: firstName,
      lastName: lastName,
      department: row.department || '',
      designation: row.designation || '',
      employeeType: row.employee_type || row.employeeType || '',
      status: row.status || 'Active',
      login: (row.status === 'Active') ? 'Enabled' : 'Disabled',
      officialEmail: row.official_email || row.officialEmail || '',
      personalEmail: row.personal_email || row.personalEmail || '',
      email: row.official_email || row.officialEmail || row.personal_email || row.personalEmail || '',
      mobile: row.mobile || row.phone || '',
      phone: row.mobile || row.phone || '',
      alternateMobile: row.alternate_mobile || row.alternateMobile || '',
      emergencyContactName: row.emergency_contact_name || row.emergencyContactName || '',
      emergencyContactNumber: row.emergency_contact_number || row.emergencyContactNumber || '',
      gender: row.gender || '',
      dob: row.dob || '',
      maritalStatus: row.marital_status || row.maritalStatus || '',
      bloodGroup: row.blood_group || row.bloodGroup || '',
      workLocation: row.work_location || row.workLocation || '',
      shiftType: row.shift_type || row.shiftType || '',
      shiftId: row.shift_id ?? row.shiftId ?? null,
      shift: row.shift ?? null,
      doj: row.doj || row.joiningDate || '',
      joiningDate: row.doj || row.joiningDate || '',
      bankName: row.bank_name || row.bankName || '',
      bankAccountNo: row.bank_account_no || row.bankAccountNo || '',
      ifscCode: row.ifsc_code || row.ifscCode || '',
      micrCode: row.micr_code || row.micrCode || '',
      panNumber: row.pan_number || row.panNumber || '',
      uanNumber: row.uan_number || row.uanNumber || '',
      pfNumber: row.pf_number || row.pfNumber || '',
      isManager: row.is_manager ?? row.isManager ?? false,
      userRole: row.user_role || row.userRole || 'Employee',
      directReportsCount: row.direct_reports_count ?? row.directReportsCount ?? 0
    };
  }

  getDashboardStats(): Observable<ManagerDashboardStats> {
    return this.http.get<ManagerDashboardStats>(`${this.apiUrl}/dashboard-stats`);
  }

  getAttendanceTrend(period: string = 'This Month'): Observable<AttendanceTrendData> {
    return this.http.get<AttendanceTrendData>(`${this.apiUrl}/attendance-trend`, {
      params: { period }
    });
  }

  getTeam(page: number = 1, limit: number = 10, search: string = ''): Observable<PaginatedResult<Employee>> {
    const params: any = { page, limit };
    if (search && search.trim()) {
      params.search = search.trim();
    }
    return this.http.get<any>(`${this.apiUrl}/team`, { params }).pipe(
      map(res => {
        const rawList = res?.data || res?.items || (Array.isArray(res) ? res : []);
        return {
          data: rawList.map((row: any) => this.mapEmployee(row)),
          total: res?.total ?? rawList.length,
          page: res?.page ?? page,
          limit: res?.limit ?? limit
        };
      })
    );
  }

  getTeamMember(employeeId: string | number): Observable<Employee> {
    return this.http.get<any>(`${this.apiUrl}/team/${employeeId}`).pipe(
      map(row => this.mapEmployee(row))
    );
  }

  private mapAttendance(row: any): any {
    if (!row) return row;
    const employeeName = row.employeeName || row.employee_name || row.employee || (row.employeeId ? `Employee #${row.employeeId}` : 'Employee');
    const employeeCode = row.employeeCode || row.employee_code || row.emp_code || (row.employeeId ? `EMP-${String(row.employeeId).padStart(4, '0')}` : '—');
    const totalWorkingMinutes = row.totalWorkingMinutes ?? row.total_working_minutes ?? row.grandTotalMinutes ?? row.grand_total_minutes ?? 0;
    
    let totalWorkingHours = row.totalWorkingHours || row.total_working_hours;
    if (!totalWorkingHours) {
      if (totalWorkingMinutes > 0) {
        totalWorkingHours = `${Math.floor(totalWorkingMinutes / 60)}h ${totalWorkingMinutes % 60}m`;
      } else if (row.punchIn && !row.punchOut) {
        totalWorkingHours = 'Working';
      } else if (['absent', 'leave', 'on leave'].includes((row.status || '').toLowerCase())) {
        totalWorkingHours = '—';
      } else {
        totalWorkingHours = '0h 0m';
      }
    }

    return {
      ...row,
      employeeName,
      employeeCode,
      totalWorkingHours,
      punchInTime: row.punchInTime || row.punch_in || row.punchIn,
      punchOutTime: row.punchOutTime || row.punch_out || row.punchOut,
      lateMinutes: row.lateMinutes ?? row.late_minutes ?? 0,
      status: row.status || 'Present'
    };
  }

  getTeamAttendance(params: {
    page?: number;
    limit?: number;
    fromDate?: string;
    toDate?: string;
    employeeId?: number;
    status?: string;
    search?: string;
  }): Observable<any> {
    const queryParams: any = {
      page: params.page || 1,
      limit: params.limit || 10
    };
    if (params.fromDate) queryParams.fromDate = params.fromDate;
    if (params.toDate) queryParams.toDate = params.toDate;
    if (params.employeeId) queryParams.employeeId = params.employeeId;
    if (params.status) queryParams.status = params.status;
    if (params.search) queryParams.search = params.search;

    return this.http.get<any>(`${this.apiUrl}/attendance`, { params: queryParams }).pipe(
      map(res => {
        if (!res || !res.items) return res;
        return {
          ...res,
          items: res.items.map((item: any) => this.mapAttendance(item))
        };
      })
    );
  }

  getTeamLeaveRequests(page: number = 1, pageSize: number = 10, status: string = ''): Observable<{
    items: TimeOffRequest[];
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
  }> {
    const params: any = { page, pageSize };
    if (status) params.status = status;
    return this.http.get<any>(`${this.apiUrl}/leave-requests`, { params });
  }

  getLeaveRequestDetail(requestId: number): Observable<TimeOffRequest> {
    return this.http.get<TimeOffRequest>(`${this.apiUrl}/leave-requests/${requestId}`);
  }

  approveLeaveRequest(requestId: number, comment?: string): Observable<TimeOffRequest> {
    return this.http.post<TimeOffRequest>(`${this.apiUrl}/leave-requests/${requestId}/approve`, {
      comment: comment || ''
    });
  }

  rejectLeaveRequest(requestId: number, comment: string): Observable<TimeOffRequest> {
    return this.http.post<TimeOffRequest>(`${this.apiUrl}/leave-requests/${requestId}/reject`, {
      comment
    });
  }

  sendAttendanceReminder(): Observable<{ success: boolean; count: number; message: string; recipients?: string[] }> {
    return this.http.post<{ success: boolean; count: number; message: string; recipients?: string[] }>(
      `${this.apiUrl}/send-attendance-reminder`,
      {}
    );
  }

  getTeamPerformance(): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/team-performance`);
  }
}


