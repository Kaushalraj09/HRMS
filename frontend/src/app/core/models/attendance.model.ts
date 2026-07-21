export type AttendanceStatus = 'Present' | 'Working' | 'Absent' | 'Not Marked' | 'Half Day' | 'Time Off';
export type WorkMode = 'Office' | 'Remote' | 'Hybrid';

export interface AttendanceRecord {
  id: string;
  code: string;
  name: string;
  department: string;
  date: string;
  scheduledStart?: string;
  scheduledEnd?: string;
  taskDescription?: string;
  punchIn: string;
  punchOut: string;
  hours: string;
  status: AttendanceStatus;
  workMode?: string;
  punchInAddress?: string;
  punchOutAddress?: string;
  punchInImage?: string;
  punchOutImage?: string;
  isWorking?: boolean;
  attendanceStatus?: string;
  badgeColor?: string;
}

export interface AttendanceMetrics {
  present: number;
  working: number;
  absent: number;
  notMarked: number;
}

export interface PaginatedAttendance {
  data: AttendanceRecord[];
  total: number;
  metrics: AttendanceMetrics;
}

export interface EmployeeTimesheetRow {
  date: string;
  day: string;
  scheduledStart?: string;
  scheduledEnd?: string;
  taskDescription?: string;
  entry: string;
  exit: string;
  late?: string;
  total: string;
  overtime: string;
  break: string;
  grandTotal: string;
  status: AttendanceStatus;
}

export interface EmployeeAttendanceSummaryItem {
  label: string;
  value: number;
  icon: string;
}

export interface EmployeeTimelineEvent {
  date: string;
  time: string;
  title: string;
  location: string;
  taskDescription?: string;
  type?: 'schedule' | 'punch-in' | 'punch-out' | 'time-off';
}

export interface TodayAttendanceState {
  isWorking: boolean;
  status: string;
  totalWorkedSeconds: number;
  approvedSeconds: number;
  remainingSeconds: number;
  shiftTotalSeconds: number;
  shiftElapsedSeconds: number;
  shiftStart: string;
  shiftEnd: string;
  workMode: WorkMode;
  punchIn?: string | null;
  punchOut?: string | null;
  punchInLatitude?: number | null;
  punchInLongitude?: number | null;
  punchInAddress?: string | null;
  punchOutLatitude?: number | null;
  punchOutLongitude?: number | null;
  punchOutAddress?: string | null;
  punchInImage?: string | null;
  punchOutImage?: string | null;
  attendanceStatus?: string;
  badgeColor?: string;
  yesterdayAutoCheckedOut?: boolean;
  requiresRegularization?: boolean;
  overtimeApproved?: boolean;
  overtimeExtended?: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}
