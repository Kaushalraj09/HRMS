export type UserRole = 'admin' | 'hr' | 'employee';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SessionUser {
  id: string;
  email: string;
  displayName: string;
  role: UserRole;
  linkedEmployeeId?: string;
  linkedHrId?: string;
  status: 'Active' | 'Inactive';
  accessibleDashboards?: string[];
  activeDashboard?: 'HR' | 'EMPLOYEE' | 'MASTER';
}

export interface LoginResponse {
  accessToken?: string;
  refreshToken?: string;
  tokenType?: 'bearer';
  expiresIn?: number;
  me?: SessionUser;
  requiresDashboardSelection?: boolean;
  availableDashboards?: string[];
  user?: SessionUser;
}

export interface ChangePasswordPayload {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}
