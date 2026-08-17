export interface DashboardStatCard {
  icon: string;
  label: string;
  value: string;
}

export interface DashboardTableRow {
  primary: string;
  secondary: string;
  tertiary?: string;
  status?: string;
  actionLabel?: string;
}

export interface DepartmentDistributionItem {
  name: string;
  count: number;
  percentage: number;
  color: string;
}

export interface MonthlyHiringItem {
  month: string;
  count: number;
}

export interface AttendanceOverviewPoint {
  date: string;
  percentage: number;
  present: number;
  total: number;
}

export interface RecentJoinerItem {
  id: number;
  name: string;
  designation: string;
  department: string;
  doj: string;
  avatar?: string | null;
  initials: string;
}

export interface BirthdayItem {
  id: number;
  name: string;
  designation: string;
  department: string;
  dob: string;
  avatar?: string | null;
  initials: string;
  isToday?: boolean;
}

export interface PendingApprovalsSummary {
  leaveRequests: number;
  timeOffRequests: number;
  regularizationRequests: number;
  expenseClaims: number;
}

export interface AdminProfileInfo {
  name: string;
  code: string;
  role: string;
  department: string;
  shift: string;
  status: string;
}

export interface AdminDashboardData {
  cards: DashboardStatCard[];
  hrUsers: DashboardTableRow[];
  employees: DashboardTableRow[];
  
  totalEmployees?: number;
  employeeGrowthCount?: number;
  employeeGrowthRate?: number;
  attendanceRate?: number;
  attendanceGrowthRate?: number;
  pendingLeavesCount?: number;
  payrollStatus?: string;
  payrollPeriod?: string;
  
  adminProfile?: AdminProfileInfo;
  attendanceOverview?: AttendanceOverviewPoint[];
  departmentDistribution?: DepartmentDistributionItem[];
  monthlyHiringTrend?: MonthlyHiringItem[];
  recentJoiners?: RecentJoinerItem[];
  todayBirthdays?: BirthdayItem[];
  pendingApprovals?: PendingApprovalsSummary;
}

export interface WeeklyAttendanceTrendItem {
  date: string;
  present: number;
  absent: number;
  leave: number;
  wfh: number;
  total: number;
  percentage: number;
}

export interface HrDashboardData {
  totalEmployees: number;
  presentEmployees: number;
  checkedInEmployees: number;
  checkedOutEmployees: number;
  notMarkedEmployees: number;
  absentEmployees?: number;
  workModeBreakdown: number[];
  genderBreakdown: number[];
  quickStats: Array<{ total: number; name: string }>;
  recentTimeSheets: Array<{
    employee: string;
    employeeCode: string;
    date: string;
    punchIn: string;
    punchOut: string;
    breakTime: string;
    overtime: string;
    totalHours: string;
    status: string;
  }>;
  upcomingEvents: Array<{
    name: string;
    note: string;
    role: string;
  }>;
  weeklyAttendanceTrend: WeeklyAttendanceTrendItem[];
}

