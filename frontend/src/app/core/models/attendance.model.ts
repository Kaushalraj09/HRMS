export type AttendanceStatus = 'Present' | 'Checked In' | 'Checked Out' | 'Not Marked' | 'Working' | 'Not working';
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
  checkIn: string;
  checkOut: string;
  hours: string;
  status: AttendanceStatus;
}

export interface AttendanceMetrics {
  present: number;
  checkedIn: number;
  notMarked: number;
  checkedOut: number;
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
  type?: 'schedule' | 'punch-in' | 'punch-out';
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
  checkIn?: string | null;
  checkOut?: string | null;
}
