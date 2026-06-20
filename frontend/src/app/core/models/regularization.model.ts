export type RegularizationReasonType =
  | 'missed_punch'
  | 'late_sync'
  | 'forgot_punch_out'
  | 'forgot_punch_in'
  | 'system_issue'
  | 'other';

export interface RegularizationCreatePayload {
  attendanceDate: string;
  requestedPunchIn?: string | null;
  requestedPunchOut?: string | null;
  reasonType: RegularizationReasonType | string;
  reasonText: string;
}

export interface RegularizationRequestItem {
  id: number;
  employeeId: number;
  employeeName?: string | null;
  employeeCode?: string | null;
  attendanceDate: string;
  requestedPunchIn?: string | null;
  requestedPunchOut?: string | null;
  reasonType: string;
  reasonText: string;
  status: 'pending' | 'approved' | 'rejected';
  reviewedBy?: number | null;
  reviewedByName?: string | null;
  reviewedAt?: string | null;
  reviewComment?: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface RegularizationDecisionPayload {
  status: 'approved' | 'rejected';
  reviewComment?: string | null;
}
