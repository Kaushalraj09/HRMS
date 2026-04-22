import { Injectable } from '@angular/core';

import { ChangePasswordPayload, LoginRequest, LoginResponse, SessionUser, UserRole } from '../models/auth.model';
import { AttendanceMetrics, AttendanceRecord, AttendanceStatus, EmployeeTimesheetRow, TodayAttendanceState, WorkMode } from '../models/attendance.model';
import { AdminDashboardData, HrDashboardData } from '../models/dashboard.model';
import { Employee, EmployeeDetailView, EmployeePayload, PaginatedResult } from '../models/employee.model';
import { CreateHrPayload, HrUser } from '../models/hr.model';
import { EmployeeProfile } from '../models/profile.model';

interface UserAccountRecord {
  id: string;
  email: string;
  password: string;
  displayName: string;
  role: UserRole;
  status: 'Active' | 'Inactive';
  linkedEmployeeId?: string;
  linkedHrId?: string;
}

interface AttendanceDayState {
  id: string;
  employeeId: string;
  date: string;
  checkIn: string;
  checkOut: string;
  breakMinutes: number;
  overtimeMinutes: number;
  workMode: WorkMode;
  status: AttendanceStatus;
}

interface Phase1State {
  users: UserAccountRecord[];
  hrs: HrUser[];
  employees: Employee[];
  attendance: AttendanceDayState[];
}

interface EmployeeFilters {
  page: number;
  limit: number;
  search: string;
  department: string;
  type: string;
  status: string;
}

interface HrFilters {
  page: number;
  limit: number;
  search: string;
  status: string;
}

interface AttendanceFilters {
  page: number;
  limit: number;
  fromDate: string;
  toDate: string;
  search: string;
  department: string;
  status: string;
}

@Injectable({
  providedIn: 'root'
})
export class Phase1StoreService {
  private readonly stateKey = 'aivan_hrms_phase1_state_v1';
  private readonly sessionKey = 'aivan_hrms_phase1_session_v1';
  private readonly tokenKey = 'aivan_hrms_phase1_token_v1';
  private readonly userKey = 'aivan_hrms_phase1_user_v1';

  private state: Phase1State = this.loadState();

  login(payload: LoginRequest): SessionUser | null {
    const user = this.state.users.find(account =>
      account.email.toLowerCase() === payload.email.toLowerCase() &&
      account.password === payload.password &&
      account.status === 'Active'
    );

    if (!user) {
      return null;
    }

    this.saveSession(user.id);
    this.persistUser(this.toSessionUser(user));
    return this.toSessionUser(user);
  }

  saveBackendSession(response: LoginResponse): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(this.tokenKey, response.accessToken);
      localStorage.setItem(this.userKey, JSON.stringify(response.me));
      localStorage.setItem(this.sessionKey, String(response.me.id));
    }
  }

  logout(): void {
    this.removeSession();
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(this.tokenKey);
      localStorage.removeItem(this.userKey);
    }
  }

  getCurrentUser(): SessionUser | null {
    if (typeof localStorage !== 'undefined') {
      const userJson = localStorage.getItem(this.userKey);
      if (userJson) {
        try {
          return JSON.parse(userJson) as SessionUser;
        } catch {
          return null;
        }
      }
    }

    const currentId = this.getSessionUserId();
    if (!currentId) {
      return null;
    }

    const user = this.state.users.find(item => String(item.id) === String(currentId));
    return user ? this.toSessionUser(user) : null;
  }

  isLoggedIn(): boolean {
    return !!this.getCurrentUser();
  }

  canAccess(roles: UserRole[]): boolean {
    const user = this.getCurrentUser();
    return !!user && roles.includes(user.role);
  }

  getLandingRoute(role: UserRole): string {
    if (role === 'admin') {
      return '/master-dashboard';
    }
    if (role === 'hr') {
      return '/hr-dashboard';
    }
    return '/emp-dashboard';
  }

  getAdminDashboardData(): AdminDashboardData {
    const todayMetrics = this.getAttendanceMetricsForDate(this.todayIsoDate());
    const activeUsers = this.state.users.filter(user => user.status === 'Active').length;

    return {
      cards: [
        { icon: 'fas fa-user-shield', label: 'Total HR Users', value: String(this.state.hrs.length) },
        { icon: 'fas fa-users', label: 'Total Employees', value: String(this.state.employees.length) },
        { icon: 'fas fa-user-check', label: 'Active Accounts', value: String(activeUsers) },
        { icon: 'fas fa-calendar-check', label: 'Present Today', value: String(todayMetrics.present + todayMetrics.checkedOut + todayMetrics.checkedIn) }
      ],
      hrUsers: this.state.hrs.slice(0, 6).map(hr => ({
        primary: hr.fullName,
        secondary: hr.email,
        tertiary: `${hr.department} · ${hr.designation}`,
        status: hr.status
      })),
      employees: this.state.employees.slice(0, 6).map(employee => ({
        primary: employee.name,
        secondary: employee.officialEmail,
        tertiary: `${employee.department} · ${employee.designation}`,
        status: employee.status
      }))
    };
  }

  getHrDashboardData(): HrDashboardData {
    const metrics = this.getAttendanceMetricsForDate(this.todayIsoDate());
    const todayRows = this.toAttendanceRows(this.state.attendance.filter(record => record.date === this.todayIsoDate())).slice(0, 8);
    const officeCount = this.state.employees.filter(employee => employee.workLocation.toLowerCase().includes('office')).length;
    const remoteCount = Math.max(0, this.state.employees.length - officeCount);
    const maleCount = this.state.employees.filter(employee => employee.gender === 'Male').length;
    const femaleCount = this.state.employees.filter(employee => employee.gender === 'Female').length;

    return {
      totalEmployees: this.state.employees.length,
      presentEmployees: metrics.present,
      checkedInEmployees: metrics.checkedIn,
      checkedOutEmployees: metrics.checkedOut,
      notMarkedEmployees: metrics.notMarked,
      workModeBreakdown: [remoteCount, officeCount],
      genderBreakdown: [femaleCount, maleCount],
      quickStats: [
        { total: this.state.hrs.length, name: 'HR Users' },
        { total: new Set(this.state.employees.map(employee => employee.department)).size, name: 'Departments' },
        { total: this.state.employees.filter(employee => employee.status === 'Active').length, name: 'Active Employees' },
        { total: this.state.attendance.filter(record => record.overtimeMinutes > 0).length, name: 'Overtime Entries' }
      ],
      recentTimeSheets: todayRows.map(row => ({
        employee: row.name,
        date: row.date,
        punchIn: row.checkIn || '-',
        punchOut: row.checkOut || '-',
        breakTime: this.findAttendanceByCodeAndDate(row.code, row.date)?.breakMinutes ? `${this.findAttendanceByCodeAndDate(row.code, row.date)?.breakMinutes} mins` : '0 mins',
        overtime: this.findAttendanceByCodeAndDate(row.code, row.date)?.overtimeMinutes ? `${this.findAttendanceByCodeAndDate(row.code, row.date)?.overtimeMinutes} mins` : '0 mins',
        totalHours: row.hours,
        status: row.status
      }))
    };
  }

  listEmployees(filters: EmployeeFilters): PaginatedResult<Employee> {
    let filtered = [...this.state.employees];

    if (filters.search) {
      const searchValue = filters.search.toLowerCase();
      filtered = filtered.filter(employee =>
        employee.name.toLowerCase().includes(searchValue) ||
        employee.employeeCode.toLowerCase().includes(searchValue) ||
        employee.department.toLowerCase().includes(searchValue) ||
        employee.officialEmail.toLowerCase().includes(searchValue)
      );
    }

    if (filters.department) {
      filtered = filtered.filter(employee => employee.department === filters.department);
    }

    if (filters.type) {
      filtered = filtered.filter(employee => employee.employeeType === filters.type);
    }

    if (filters.status) {
      filtered = filtered.filter(employee => employee.status === filters.status);
    }

    const startIndex = (filters.page - 1) * filters.limit;
    return {
      data: filtered.slice(startIndex, startIndex + filters.limit),
      total: filtered.length
    };
  }

  listHrs(filters: HrFilters): PaginatedResult<HrUser> {
    let filtered = [...this.state.hrs];

    if (filters.search) {
      const searchValue = filters.search.toLowerCase();
      filtered = filtered.filter(hr =>
        hr.fullName.toLowerCase().includes(searchValue) ||
        hr.hrCode.toLowerCase().includes(searchValue) ||
        hr.email.toLowerCase().includes(searchValue) ||
        hr.department.toLowerCase().includes(searchValue)
      );
    }

    if (filters.status) {
      filtered = filtered.filter(hr => hr.status === filters.status);
    }

    const startIndex = (filters.page - 1) * filters.limit;
    return {
      data: filtered.slice(startIndex, startIndex + filters.limit),
      total: filtered.length
    };
  }

  getEmployeeById(employeeId: string): EmployeeDetailView | null {
    const employee = this.state.employees.find(item => item.id === employeeId);
    if (!employee) {
      return null;
    }

    const user = this.state.users.find(item => item.id === employee.userId);

    return {
      employee,
      managerName: 'Assigned HR Team',
      loginEmail: user?.email ?? employee.officialEmail,
      temporaryPasswordHint: 'Temp password set during account creation'
    };
  }

  createEmployee(payload: EmployeePayload): { success: boolean; message: string; employee: Employee } {
    const userId = this.createId('user');
    const employeeId = this.createId('emp');
    const employeeCode = payload.employmentInfo.employeeCode || this.nextEmployeeCode();
    const loginEmail = payload.accountAccess?.loginEmail || payload.contactInfo.officialEmail;
    const temporaryPassword = payload.accountAccess?.temporaryPassword || 'Employee@123';

    const employee: Employee = {
      id: employeeId,
      userId,
      employeeCode,
      name: `${payload.personalInfo.firstName} ${payload.personalInfo.lastName}`.trim(),
      firstName: payload.personalInfo.firstName,
      lastName: payload.personalInfo.lastName,
      department: payload.employmentInfo.department || 'Engineering',
      designation: payload.employmentInfo.designation || 'Associate',
      employeeType: payload.employmentInfo.employeeType || 'Full-Time',
      status: 'Active',
      login: 'Enabled',
      officialEmail: payload.contactInfo.officialEmail,
      personalEmail: payload.contactInfo.personalEmail,
      mobile: payload.contactInfo.mobile,
      alternateMobile: payload.contactInfo.alternateMobile,
      emergencyContactName: payload.contactInfo.emergencyContactName,
      emergencyContactNumber: payload.contactInfo.emergencyContactNumber,
      gender: payload.personalInfo.gender || 'Other',
      dob: payload.personalInfo.dob,
      maritalStatus: payload.personalInfo.maritalStatus,
      bloodGroup: payload.personalInfo.bloodGroup,
      workLocation: payload.employmentInfo.workLocation || 'Main Office',
      shiftType: payload.employmentInfo.shiftType || 'General Shift',
      doj: payload.employmentInfo.doj
    };

    const user: UserAccountRecord = {
      id: userId,
      email: loginEmail,
      password: temporaryPassword,
      displayName: employee.name,
      role: 'employee',
      status: 'Active',
      linkedEmployeeId: employee.id
    };

    this.state = {
      ...this.state,
      users: [user, ...this.state.users],
      employees: [employee, ...this.state.employees],
      attendance: [this.createBlankAttendanceRecord(employee), ...this.state.attendance]
    };
    this.persistState();

    return {
      success: true,
      message: `${employee.name} created successfully. Login email: ${loginEmail}`,
      employee
    };
  }

  updateEmployee(employeeId: string, payload: EmployeePayload): { success: boolean; message: string } {
    const employee = this.state.employees.find(item => item.id === employeeId);
    if (!employee) {
      return { success: false, message: 'Employee not found' };
    }

    const updatedEmployee: Employee = {
      ...employee,
      name: `${payload.personalInfo.firstName} ${payload.personalInfo.lastName}`.trim(),
      firstName: payload.personalInfo.firstName,
      lastName: payload.personalInfo.lastName,
      gender: payload.personalInfo.gender,
      dob: payload.personalInfo.dob,
      maritalStatus: payload.personalInfo.maritalStatus,
      bloodGroup: payload.personalInfo.bloodGroup,
      department: payload.employmentInfo.department,
      designation: payload.employmentInfo.designation,
      employeeType: payload.employmentInfo.employeeType,
      workLocation: payload.employmentInfo.workLocation,
      shiftType: payload.employmentInfo.shiftType,
      doj: payload.employmentInfo.doj,
      officialEmail: payload.contactInfo.officialEmail,
      personalEmail: payload.contactInfo.personalEmail,
      mobile: payload.contactInfo.mobile,
      alternateMobile: payload.contactInfo.alternateMobile,
      emergencyContactName: payload.contactInfo.emergencyContactName,
      emergencyContactNumber: payload.contactInfo.emergencyContactNumber
    };

    this.state = {
      ...this.state,
      employees: this.state.employees.map(item => item.id === employeeId ? updatedEmployee : item),
      users: this.state.users.map(item => item.id === employee.userId ? { ...item, email: payload.accountAccess?.loginEmail || payload.contactInfo.officialEmail, displayName: updatedEmployee.name } : item)
    };
    this.persistState();

    return { success: true, message: 'Employee updated successfully' };
  }

  createHr(payload: CreateHrPayload): { success: boolean; message: string; hr: HrUser } {
    const userId = this.createId('user');
    const hrId = this.createId('hr');
    const fullName = payload.fullName.trim();
    const hr: HrUser = {
      id: hrId,
      userId,
      hrCode: this.nextHrCode(),
      fullName,
      email: payload.email,
      phone: payload.phone,
      department: payload.department,
      designation: payload.designation,
      status: payload.status,
      login: payload.status === 'Active' ? 'Enabled' : 'Disabled',
      createdAt: this.todayIsoDate()
    };

    const user: UserAccountRecord = {
      id: userId,
      email: payload.email,
      password: payload.temporaryPassword,
      displayName: fullName,
      role: 'hr',
      status: payload.status,
      linkedHrId: hr.id
    };

    this.state = {
      ...this.state,
      users: [user, ...this.state.users],
      hrs: [hr, ...this.state.hrs]
    };
    this.persistState();

    return {
      success: true,
      message: `${payload.fullName} created successfully as HR`,
      hr
    };
  }

  listAttendance(filters: AttendanceFilters): { result: { data: AttendanceRecord[]; total: number; metrics: AttendanceMetrics } } {
    let records = this.toAttendanceRows(this.state.attendance);

    if (filters.search) {
      const searchValue = filters.search.toLowerCase();
      records = records.filter(record =>
        record.name.toLowerCase().includes(searchValue) ||
        record.code.toLowerCase().includes(searchValue)
      );
    }

    if (filters.department) {
      records = records.filter(record => record.department === filters.department);
    }

    if (filters.status) {
      records = records.filter(record => record.status === filters.status);
    }

    if (filters.fromDate) {
      records = records.filter(record => record.date >= filters.fromDate);
    }

    if (filters.toDate) {
      records = records.filter(record => record.date <= filters.toDate);
    }

    const startIndex = (filters.page - 1) * filters.limit;
    const paginated = records.slice(startIndex, startIndex + filters.limit);

    return {
      result: {
        data: paginated,
        total: records.length,
        metrics: {
          present: records.filter(record => record.status === 'Present').length,
          checkedIn: records.filter(record => record.status === 'Checked In').length,
          checkedOut: records.filter(record => record.status === 'Checked Out').length,
          notMarked: records.filter(record => record.status === 'Not Marked').length
        }
      }
    };
  }

  getMyTimesheets(): EmployeeTimesheetRow[] {
    const currentUser = this.getCurrentUser();
    if (!currentUser?.linkedEmployeeId) {
      return [];
    }

    return this.state.attendance
      .filter(record => record.employeeId === currentUser.linkedEmployeeId)
      .sort((left, right) => right.date.localeCompare(left.date))
      .map(record => this.toEmployeeTimesheetRow(record));
  }

  getTodayAttendanceState(): TodayAttendanceState {
    const currentUser = this.getCurrentUser();
    const employeeId = currentUser?.linkedEmployeeId;

    if (!employeeId) {
      return {
        isPunchedIn: false,
        status: 'Not Marked',
        approvedHours: 2,
        remainingHours: 8,
        workMode: 'Office'
      };
    }

    const record = this.getOrCreateTodayAttendance(employeeId);
    return {
      isPunchedIn: !!record.checkIn && !record.checkOut,
      status: record.status,
      approvedHours: 2,
      remainingHours: 8,
      workMode: record.workMode
    };
  }

  toggleMyPunch(workMode: WorkMode): TodayAttendanceState {
    const currentUser = this.getCurrentUser();
    const employeeId = currentUser?.linkedEmployeeId;
    if (!employeeId) {
      return this.getTodayAttendanceState();
    }

    const today = this.todayIsoDate();
    const currentTime = this.currentTimeString();
    const existing = this.getOrCreateTodayAttendance(employeeId);
    const updated = { ...existing, workMode };

    if (!existing.checkIn) {
      updated.checkIn = currentTime;
      updated.status = 'Checked In';
    } else if (!existing.checkOut) {
      updated.checkOut = currentTime;
      updated.status = 'Checked Out';
      updated.breakMinutes = 45;
      updated.overtimeMinutes = 20;
    } else {
      updated.checkIn = currentTime;
      updated.checkOut = '';
      updated.breakMinutes = 0;
      updated.overtimeMinutes = 0;
      updated.status = 'Checked In';
    }

    this.state = {
      ...this.state,
      attendance: this.state.attendance.map(record =>
        record.employeeId === employeeId && record.date === today ? updated : record
      )
    };
    this.persistState();

    return this.getTodayAttendanceState();
  }

  getAttendanceSummaryItems(): Array<{ label: string; value: number; icon: string }> {
    const rows = this.getMyTimesheets();

    return [
      { label: 'Total Days', value: rows.length, icon: 'fas fa-calendar total blue-icon' },
      { label: 'Worked Days', value: rows.filter(row => row.status !== 'Not Marked').length, icon: 'fas fa-calendar-check worked blue-icon' },
      { label: 'Present', value: rows.filter(row => row.status === 'Present' || row.status === 'Checked Out').length, icon: 'fas fa-check-circle blue-icon' },
      { label: 'Checked In', value: rows.filter(row => row.status === 'Checked In').length, icon: 'fas fa-user-check blue-icon' },
      { label: 'Not Marked', value: rows.filter(row => row.status === 'Not Marked').length, icon: 'fas fa-user-times unapproved blue-icon' }
    ];
  }

  getEmployeeProfile(): EmployeeProfile | null {
    const currentUser = this.getCurrentUser();
    const employee = this.state.employees.find(item => item.id === currentUser?.linkedEmployeeId);
    if (!employee) {
      return null;
    }

    return {
      id: employee.id,
      employeeId: employee.employeeCode,
      firstName: employee.firstName,
      lastName: employee.lastName,
      initials: `${employee.firstName[0] ?? ''}${employee.lastName[0] ?? ''}`.toUpperCase(),
      role: employee.designation,
      department: employee.department,
      shift: employee.shiftType,
      status: employee.status,
      personalDetails: {
        firstName: employee.firstName,
        lastName: employee.lastName,
        gender: employee.gender,
        dateOfBirth: employee.dob,
        maritalStatus: employee.maritalStatus,
        bloodGroup: employee.bloodGroup
      },
      contactDetails: {
        officialEmail: employee.officialEmail,
        personalEmail: employee.personalEmail,
        mobileNumber: employee.mobile,
        alternateMobile: employee.alternateMobile,
        location: employee.workLocation
      }
    };
  }

  updateEmployeeProfile(profile: EmployeeProfile): { success: boolean; message: string } {
    const employeeIdx = this.state.employees.findIndex(e => e.id === profile.id);
    if (employeeIdx === -1) {
      return { success: false, message: 'Employee profile not found' };
    }

    const employee = this.state.employees[employeeIdx];
    const updatedEmployee: Employee = {
      ...employee,
      firstName: profile.personalDetails.firstName,
      lastName: profile.personalDetails.lastName,
      name: `${profile.personalDetails.firstName} ${profile.personalDetails.lastName}`.trim(),
      gender: profile.personalDetails.gender,
      dob: profile.personalDetails.dateOfBirth,
      maritalStatus: profile.personalDetails.maritalStatus || '',
      bloodGroup: profile.personalDetails.bloodGroup || '',
      mobile: profile.contactDetails.mobileNumber,
      alternateMobile: profile.contactDetails.alternateMobile || '',
      personalEmail: profile.contactDetails.personalEmail || '',
      workLocation: profile.contactDetails.location
    };

    this.state = {
      ...this.state,
      employees: this.state.employees.map(e => e.id === profile.id ? updatedEmployee : e),
      users: this.state.users.map(u => u.id === employee.userId ? { ...u, displayName: updatedEmployee.name } : u)
    };

    this.persistState();
    return { success: true, message: 'Profile updated successfully' };
  }

  updateCurrentPassword(payload: ChangePasswordPayload): { success: boolean; message: string } {
    const currentUser = this.getCurrentUser();
    if (!currentUser) {
      throw new Error('Session expired. Please login again.');
    }

    const account = this.state.users.find(user => user.id === currentUser.id);
    if (!account || account.password !== payload.currentPassword) {
      throw new Error('Current password is incorrect');
    }

    if (payload.newPassword !== payload.confirmPassword) {
      throw new Error('Passwords do not match');
    }

    this.state = {
      ...this.state,
      users: this.state.users.map(user => user.id === currentUser.id ? { ...user, password: payload.newPassword } : user)
    };
    this.persistState();

    return { success: true, message: 'Password updated successfully' };
  }

  private loadState(): Phase1State {
    if (typeof localStorage === 'undefined') {
      return this.seedState();
    }

    const raw = localStorage.getItem(this.stateKey);
    if (!raw) {
      const seed = this.seedState();
      localStorage.setItem(this.stateKey, JSON.stringify(seed));
      return seed;
    }

    try {
      const parsed = JSON.parse(raw) as Partial<Phase1State>;
      const normalized = this.normalizeState(parsed);
      localStorage.setItem(this.stateKey, JSON.stringify(normalized));
      return normalized;
    } catch {
      const seed = this.seedState();
      localStorage.setItem(this.stateKey, JSON.stringify(seed));
      return seed;
    }
  }

  private persistState(): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(this.stateKey, JSON.stringify(this.state));
    }
  }

  private persistUser(user: SessionUser): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(this.userKey, JSON.stringify(user));
    }
  }

  private saveSession(userId: string): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(this.sessionKey, userId);
    }
  }

  private getSessionUserId(): string | null {
    if (typeof localStorage === 'undefined') {
      return null;
    }
    return localStorage.getItem(this.sessionKey);
  }

  private removeSession(): void {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem(this.sessionKey);
    }
  }

  private toSessionUser(user: UserAccountRecord): SessionUser {
    return {
      id: user.id,
      email: user.email,
      displayName: user.displayName,
      role: user.role,
      linkedEmployeeId: user.linkedEmployeeId,
      linkedHrId: user.linkedHrId,
      status: user.status
    };
  }

  private toAttendanceRows(records: AttendanceDayState[]): AttendanceRecord[] {
    return records
      .slice()
      .sort((left, right) => right.date.localeCompare(left.date))
      .map(record => {
        const employee = this.state.employees.find(item => item.id === record.employeeId);
        return {
          id: record.id,
          code: employee?.employeeCode ?? 'NA',
          name: employee?.name ?? 'Unknown Employee',
          department: employee?.department ?? 'Unknown',
          date: record.date,
          checkIn: record.checkIn,
          checkOut: record.checkOut,
          hours: this.formatHours(this.calculateWorkMinutes(record)),
          status: record.status
        };
      });
  }

  private toEmployeeTimesheetRow(record: AttendanceDayState): EmployeeTimesheetRow {
    const totalMinutes = this.calculateWorkMinutes(record);
    const grandTotal = totalMinutes + record.overtimeMinutes;

    return {
      date: record.date,
      day: new Date(record.date).toLocaleDateString('en-US', { weekday: 'short' }),
      entry: record.checkIn || '-',
      exit: record.checkOut || '-',
      total: this.formatHours(totalMinutes),
      overtime: this.formatHours(record.overtimeMinutes),
      break: this.formatHours(record.breakMinutes),
      grandTotal: this.formatHours(grandTotal),
      status: record.status
    };
  }

  private calculateWorkMinutes(record: AttendanceDayState): number {
    if (!record.checkIn || !record.checkOut) {
      return 0;
    }

    const [inHour, inMinute] = record.checkIn.split(':').map(value => Number(value));
    const [outHour, outMinute] = record.checkOut.split(':').map(value => Number(value));
    const start = inHour * 60 + inMinute;
    const end = outHour * 60 + outMinute;
    const gross = Math.max(0, end - start);
    return Math.max(0, gross - record.breakMinutes);
  }

  private formatHours(minutes: number): string {
    if (!minutes) {
      return '0h 0m';
    }

    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return `${hrs}h ${mins}m`;
  }

  private getAttendanceMetricsForDate(date: string): AttendanceMetrics {
    const rows = this.toAttendanceRows(this.state.attendance.filter(record => record.date === date));
    return {
      present: rows.filter(row => row.status === 'Present').length,
      checkedIn: rows.filter(row => row.status === 'Checked In').length,
      checkedOut: rows.filter(row => row.status === 'Checked Out').length,
      notMarked: rows.filter(row => row.status === 'Not Marked').length
    };
  }

  private getOrCreateTodayAttendance(employeeId: string): AttendanceDayState {
    const today = this.todayIsoDate();
    const existing = this.state.attendance.find(record => record.employeeId === employeeId && record.date === today);
    if (existing) {
      return existing;
    }

    const employee = this.state.employees.find(item => item.id === employeeId);
    const created = this.createBlankAttendanceRecord(employee!);
    this.state = {
      ...this.state,
      attendance: [created, ...this.state.attendance]
    };
    this.persistState();
    return created;
  }

  private createBlankAttendanceRecord(employee: Employee): AttendanceDayState {
    return {
      id: this.createId('att'),
      employeeId: employee.id,
      date: this.todayIsoDate(),
      checkIn: '',
      checkOut: '',
      breakMinutes: 0,
      overtimeMinutes: 0,
      workMode: employee.workLocation.toLowerCase().includes('remote') ? 'Remote' : 'Office',
      status: 'Not Marked'
    };
  }

  private findAttendanceByCodeAndDate(employeeCode: string, date: string): AttendanceDayState | undefined {
    const employee = this.state.employees.find(item => item.employeeCode === employeeCode);
    return this.state.attendance.find(item => item.employeeId === employee?.id && item.date === date);
  }

  private nextEmployeeCode(): string {
    return `EMP-${String(this.state.employees.length + 1).padStart(3, '0')}`;
  }

  private nextHrCode(): string {
    return `HR-${String(this.state.hrs.length + 1).padStart(3, '0')}`;
  }

  private createId(prefix: string): string {
    return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
  }

  private todayIsoDate(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private currentTimeString(): string {
    return new Date().toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: false
    });
  }

  private seedState(): Phase1State {
    const adminId = 'seed-user-admin';
    const hrUserId = 'seed-user-hr-001';
    const hrId = 'seed-hr-001';

    const employeeOneId = 'seed-emp-001';
    const employeeTwoId = 'seed-emp-002';
    const employeeThreeId = 'seed-emp-003';

    const employeeOneUserId = 'seed-user-emp-001';
    const employeeTwoUserId = 'seed-user-emp-002';
    const employeeThreeUserId = 'seed-user-emp-003';

    const employees: Employee[] = [
      {
        id: employeeOneId,
        userId: employeeOneUserId,
        employeeCode: 'EMP-001',
        name: 'Kaushal Raj',
        firstName: 'Kaushal',
        lastName: 'Raj',
        department: 'Engineering',
        designation: 'Frontend Developer',
        employeeType: 'Full-Time',
        status: 'Active',
        login: 'Enabled',
        officialEmail: 'kaushal@aivan.com',
        personalEmail: 'kaushal.personal@gmail.com',
        mobile: '9876543210',
        alternateMobile: '9876500001',
        emergencyContactName: 'Rakesh Raj',
        emergencyContactNumber: '9876500002',
        gender: 'Male',
        dob: '1998-03-22',
        maritalStatus: 'Single',
        bloodGroup: 'B+',
        workLocation: 'Indore Office',
        shiftType: 'General Shift',
        doj: '2025-10-01'
      },
      {
        id: employeeTwoId,
        userId: employeeTwoUserId,
        employeeCode: 'EMP-002',
        name: 'Ananya Sharma',
        firstName: 'Ananya',
        lastName: 'Sharma',
        department: 'Human Resources',
        designation: 'HR Executive',
        employeeType: 'Full-Time',
        status: 'Active',
        login: 'Enabled',
        officialEmail: 'ananya@aivan.com',
        personalEmail: 'ananya.personal@gmail.com',
        mobile: '9876543211',
        alternateMobile: '9876500003',
        emergencyContactName: 'Deepak Sharma',
        emergencyContactNumber: '9876500004',
        gender: 'Female',
        dob: '1997-08-14',
        maritalStatus: 'Single',
        bloodGroup: 'O+',
        workLocation: 'Indore Office',
        shiftType: 'General Shift',
        doj: '2025-11-10'
      },
      {
        id: employeeThreeId,
        userId: employeeThreeUserId,
        employeeCode: 'EMP-003',
        name: 'Rahul Verma',
        firstName: 'Rahul',
        lastName: 'Verma',
        department: 'Finance',
        designation: 'Finance Analyst',
        employeeType: 'Full-Time',
        status: 'Active',
        login: 'Enabled',
        officialEmail: 'rahul@aivan.com',
        personalEmail: 'rahul.personal@gmail.com',
        mobile: '9876543212',
        alternateMobile: '9876500005',
        emergencyContactName: 'Alka Verma',
        emergencyContactNumber: '9876500006',
        gender: 'Male',
        dob: '1996-01-09',
        maritalStatus: 'Married',
        bloodGroup: 'A+',
        workLocation: 'Remote Home Office',
        shiftType: 'General Shift',
        doj: '2025-12-05'
      }
    ];

    const attendance = this.seedAttendance(employees);

    return {
      users: [
        {
          id: adminId,
          email: 'admin@aivan.com',
          password: 'Admin@123',
          displayName: 'Master Admin',
          role: 'admin',
          status: 'Active'
        },
        {
          id: hrUserId,
          email: 'hr@aivan.com',
          password: 'Hr@12345',
          displayName: 'Ananya Sharma',
          role: 'hr',
          status: 'Active',
          linkedHrId: hrId
        },
        {
          id: employeeOneUserId,
          email: 'kaushal@aivan.com',
          password: 'Employee@123',
          displayName: 'Kaushal Raj',
          role: 'employee',
          status: 'Active',
          linkedEmployeeId: employeeOneId
        },
        {
          id: employeeTwoUserId,
          email: 'ananya.employee@aivan.com',
          password: 'Employee@123',
          displayName: 'Ananya Sharma',
          role: 'employee',
          status: 'Active',
          linkedEmployeeId: employeeTwoId
        },
        {
          id: employeeThreeUserId,
          email: 'rahul@aivan.com',
          password: 'Employee@123',
          displayName: 'Rahul Verma',
          role: 'employee',
          status: 'Active',
          linkedEmployeeId: employeeThreeId
        }
      ],
      hrs: [
        {
          id: hrId,
          userId: hrUserId,
          hrCode: 'HR-001',
          fullName: 'Ananya Sharma',
          email: 'hr@aivan.com',
          phone: '9876500100',
          department: 'Human Resources',
          designation: 'HR Manager',
          status: 'Active',
          login: 'Enabled',
          createdAt: '2026-01-10'
        }
      ],
      employees,
      attendance
    };
  }

  private seedAttendance(employees: Employee[]): AttendanceDayState[] {
    const seedDates = [0, 1, 2, 3, 4, 5, 6].map(offset => {
      const date = new Date();
      date.setDate(date.getDate() - offset);
      return date.toISOString().slice(0, 10);
    });

    return employees.flatMap((employee, index) =>
      seedDates.map((date, dateIndex) => {
        const checkedIn = !(index === 1 && dateIndex === 0);
        const checkedOut = dateIndex !== 0 || index !== 0;
        const checkIn = checkedIn ? `${String(9 + (index % 2)).padStart(2, '0')}:${String(5 + dateIndex).padStart(2, '0')}` : '';
        const checkOut = checkedOut && checkedIn ? `${String(18 + (index % 2)).padStart(2, '0')}:${String(10 + dateIndex).padStart(2, '0')}` : '';
        const status: AttendanceStatus = !checkedIn ? 'Not Marked' : checkedOut ? 'Present' : 'Checked In';

        return {
          id: this.createId('att'),
          employeeId: employee.id,
          date,
          checkIn,
          checkOut,
          breakMinutes: checkedIn ? 45 : 0,
          overtimeMinutes: checkedOut ? 15 : 0,
          workMode: employee.workLocation.toLowerCase().includes('remote') ? 'Remote' : 'Office',
          status
        };
      })
    );
  }

  private normalizeState(state: Partial<Phase1State> | null | undefined): Phase1State {
    const seed = this.seedState();

    if (
      !state ||
      !Array.isArray(state.users) ||
      !Array.isArray(state.hrs) ||
      !Array.isArray(state.employees) ||
      !Array.isArray(state.attendance)
    ) {
      return seed;
    }

    const requiredSeedEmails = [
      'admin@aivan.com',
      'hr@aivan.com',
      'kaushal@aivan.com',
      'ananya.employee@aivan.com',
      'rahul@aivan.com'
    ];

    const existingEmails = new Set(
      state.users
        .map(user => user?.email?.toLowerCase?.())
        .filter((email): email is string => !!email)
    );

    const missingRequiredAccounts = requiredSeedEmails.some(email => !existingEmails.has(email));

    if (missingRequiredAccounts) {
      return seed;
    }

    return {
      users: state.users,
      hrs: state.hrs,
      employees: state.employees,
      attendance: state.attendance
    };
  }
}
