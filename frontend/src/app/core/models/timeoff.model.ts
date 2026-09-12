export interface TimeOffRequest {
  id: number;
  employee_id: number;
  date: string;
  leave_type: string;
  start_time: string | null;
  end_time: string | null;
  duration_hours: number;
  status: string;
  reason?: string | null;
  attachment_name?: string | null;
  employee_name?: string | null;
  batch_id?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  total_days?: number | null;
}

export interface YearlyLeaveBalance {
  leave_type_id: number;
  code: string;
  name: string;
  unit_type: string;
  year: number;
  allocated_days: number;
  used_days: number;
  pending_days: number;
  available_days: number;
  carry_forward_days: number;
  is_wfh: boolean;
  counts_as_leave: boolean;
  attendance_required: boolean;
  remote_punch_allowed: boolean;
  applicable_employee_type: string;
}

export interface GroupedTimeOffRequest {
  id: string; // the batch_id or fallback single id
  isGrouped: boolean;
  requests: TimeOffRequest[];
  
  employee_id: number;
  employee_name?: string | null;
  
  leave_type: string;
  startDate: string;
  endDate: string;
  
  totalDurationHours: number;
  
  status: string;
  reason?: string | null;
  attachment_name?: string | null;
  
  // Keep start_time / end_time for rendering time slots if all same
  start_time: string | null;
  end_time: string | null;
}

export interface TimeOffApplyResponse {
  id: number;
  employee_id: number;
  date: string;
  leave_type: string;
  start_time: string | null;
  end_time: string | null;
  duration_hours: number;
  status: string;
  approved_hours_today: number;
  remaining_hours_today: number;
  approved_seconds_today: number;
  remaining_seconds_today: number;
}
