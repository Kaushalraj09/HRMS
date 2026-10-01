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
  allow_early_punch_in?: boolean;
  early_coming_minutes?: number;
  punch_in_grace_minutes?: number;
  shift_grace_minutes?: number;
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
  description?: string;
  location_type?: 'office' | 'remote' | string;
  latitude?: number;
  longitude?: number;
  geofence_radius_meters?: number;
  is_active: boolean;
}

export interface LeaveType {
  id: number;
  name: string;
  code: string;
  unit_type?: string;
  default_balance_hours?: number;
  /** Mapped from backend `default_balance_hours` / 8 (hours → days) */
  max_days?: number;
  applicable_employee_type?: 'all' | 'office_only' | string;
  carry_forward?: boolean;
  max_consecutive_days?: number;
  counts_as_leave?: boolean;
  attendance_required?: boolean;
  remote_punch_allowed?: boolean;
  annual_entitlement_days?: number;
  is_paid?: boolean;
  is_system_defined?: boolean;
  is_editable?: boolean;
  is_deletable?: boolean;
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
