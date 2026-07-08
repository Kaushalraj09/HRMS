export interface ApprovalTask {
  id: number;
  request_type: 'timeoff' | 'regularization' | string;
  request_id: number;
  employee_id: number;
  employee_name: string;
  employee_code: string;
  details: string;
  submitted_at: string;
  status: 'Pending' | 'Approved' | 'Rejected' | string;
  comment?: string;
  reviewed_by?: number;
  reviewed_at?: string;
  duration_hours?: number;
}

export interface ApprovalDecisionPayload {
  decision: 'approved' | 'rejected' | string;
  comment?: string;
  approved_hours?: number;
}

export interface ApprovalQueueResponse {
  timeoff: ApprovalTask[];
  regularization: ApprovalTask[];
  total: number;
}
