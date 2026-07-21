export interface AttendanceSummaryRow {
  employeeId: number;
  employeeCode: string;
  employeeName: string;
  department: string | null;
  presentDays: number;
  absentDays: number;
  halfDays: number;
  leaveDays: number;
  totalWorkingMinutes: number;
  totalOvertimeMinutes: number;
}

export interface LateArrivalRow {
  employeeId: number;
  employeeCode: string;
  employeeName: string;
  department: string | null;
  date: string;
  scheduledStart: string | null;
  punchIn: string | null;
  lateMinutes: number;
}

export interface MissingPunchRow {
  employeeId: number;
  employeeCode: string;
  employeeName: string;
  department: string | null;
  date: string;
  punchIn: string | null;
  punchOut: string | null;
  status: string;
  reason: string;
}

export interface LeaveUsageRow {
  employeeId: number;
  employeeCode: string;
  employeeName: string;
  department: string | null;
  leaveType: string;
  durationHours: number;
  date: string;
  status: string;
  reason: string | null;
}

export interface HrWorkloadRow {
  hrName: string;
  pendingTimeoff: number;
  pendingRegularization: number;
  processedTimeoff: number;
  processedRegularization: number;
  totalHandled: number;
}

export interface EmployeeStatusRow {
  employeeId: number;
  employeeCode: string;
  employeeName: string;
  department: string | null;
  designation: string | null;
  status: string;
  doj: string | null;
  timeoffBalanceHours: number;
}

export interface LoginActivitySummaryRow {
  id: number;
  employeeId: number | null;
  employeeCode: string | null;
  employeeName: string;
  email: string;
  loginTime: string;
  ipAddress: string | null;
  browser: string | null;
  device: string | null;
  operatingSystem: string | null;
  status: string;
}

export interface PaginatedReportResponse<T> {
  total: number;
  page: number;
  pageSize: number;
  pages: number;
  data: T[];
}
