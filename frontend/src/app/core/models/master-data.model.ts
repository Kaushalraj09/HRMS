export interface Department {
  id: number;
  name: string;
  code?: string;
  description?: string;
  is_active: boolean;
}

export interface Designation {
  id: number;
  name: string;
  code?: string;
  description?: string;
  is_active: boolean;
}

export interface Shift {
  id: number;
  name: string;
  /** Internal DB code – auto-generated on create, preserved on update */
  code?: string;
  description?: string;
  /** HH:MM format */
  start_time: string;
  /** HH:MM format */
  end_time: string;
  working_hours?: number;
  required_work_minutes?: number;
  grace_minutes?: number;
  lunch_duration_minutes?: number;
  lunch_start_time?: string;
  lunch_end_time?: string;
  half_day_hours?: number;
  minimum_half_day_minutes?: number;
  present_hours?: number;
  minimum_present_minutes?: number;
  overtime_start_time?: string;
  overtime_allowed?: boolean;
  max_overtime_minutes?: number;
  late_mark_after_minutes?: number;
  early_exit_before_minutes?: number;
  is_night_shift?: boolean;
  timezone?: string;
  is_active: boolean;
}

export interface WorkLocation {
  id: number;
  name: string;
  /** Internal DB code – auto-generated on create, preserved on update */
  code?: string;
  /** Mapped from backend `description` field */
  address?: string;
  is_active: boolean;
}

export interface LeaveType {
  id: number;
  name: string;
  code: string;
  /** Mapped from backend `default_balance_hours` / 8 (hours → days) */
  max_days?: number;
  is_active: boolean;
}

export interface Holiday {
  id: number;
  name: string;
  /** ISO date string YYYY-MM-DD; mapped from backend `holiday_date` */
  date: string;
  is_active: boolean;
}

export interface MasterDataBootstrapResponse {
  departments: Department[];
  designations: Designation[];
  shifts: Shift[];
  workLocations: WorkLocation[];
  leaveTypes: LeaveType[];
  holidays: Holiday[];
}
