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

export interface AdminDashboardData {
  cards: DashboardStatCard[];
  hrUsers: DashboardTableRow[];
  employees: DashboardTableRow[];
}

export interface HrDashboardData {
  totalEmployees: number;
  presentEmployees: number;
  checkedInEmployees: number;
  checkedOutEmployees: number;
  notMarkedEmployees: number;
  workModeBreakdown: number[];
  genderBreakdown: number[];
  quickStats: Array<{ total: number; name: string }>;
  recentTimeSheets: Array<{
    employee: string;
    date: string;
    punchIn: string;
    punchOut: string;
    breakTime: string;
    overtime: string;
    totalHours: string;
    status: string;
  }>;
}
