export interface AttendanceRecord {
  id: string;
  code: string;
  name: string;
  department: string;
  date: string;
  checkIn: string;
  checkOut: string;
  hours: string;
  status: 'Present' | 'Checked In' | 'Not Marked' | 'Checked Out';
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
