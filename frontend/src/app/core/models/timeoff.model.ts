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
