export type DocumentStatus =
  | 'NOT_UPLOADED'
  | 'UPLOADED'
  | 'PENDING_REVIEW'
  | 'VERIFIED'
  | 'REJECTED'
  | 'RESUBMISSION_REQUIRED'
  | 'EXPIRED';

export interface DocumentType {
  id: number;
  name: string;
  code: string;
  description?: string | null;
  category: string;
  required_default: boolean;
  allowed_file_types: string;
  max_file_size_mb: number;
  multiple_allowed: boolean;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface DocumentVersion {
  id: number;
  version_number: number;
  file_name: string;
  file_size: number;
  mime_type: string;
  status: DocumentStatus | string;
  uploaded_by_name?: string | null;
  uploaded_at: string;
  verified_by_name?: string | null;
  verified_at?: string | null;
  rejected_by_name?: string | null;
  rejected_at?: string | null;
  rejection_reason?: string | null;
  remarks?: string | null;
}

export interface EmployeeDocumentItem {
  requirement_id?: number | null;
  document_type_id: number;
  document_type_name: string;
  document_type_code: string;
  category: string;
  description?: string | null;
  is_required: boolean;
  allowed_file_types: string;
  max_file_size_mb: number;
  status: DocumentStatus | string;
  due_date?: string | null;

  // Active document info
  document_id?: number | null;
  file_name?: string | null;
  file_size?: number | null;
  mime_type?: string | null;
  version?: number | null;
  uploaded_by_name?: string | null;
  uploaded_by_role?: string | null;
  uploaded_at?: string | null;
  verified_by_name?: string | null;
  verified_at?: string | null;
  rejected_by_name?: string | null;
  rejected_at?: string | null;
  rejection_reason?: string | null;
  remarks?: string | null;
  versions_count: number;
}

export interface DocumentSummaryStats {
  total_required: number;
  total_optional: number;
  uploaded: number;
  pending_review: number;
  verified: number;
  rejected: number;
  missing: number;
  completion_percentage: number;
}

export interface EmployeeDocumentsPageResponse {
  employee_id: number;
  employee_name: string;
  employee_code: string;
  department?: string | null;
  designation?: string | null;
  summary: DocumentSummaryStats;
  documents: EmployeeDocumentItem[];
}

export interface HrDocumentOverviewKPI {
  total_employees: number;
  documents_pending: number;
  documents_verified: number;
  documents_rejected: number;
  incomplete_employees: number;
  partial_employees?: number;
  complete_employees: number;
  attention_employees?: number;
  total_required_docs?: number;
  overall_compliance_rate: number;
  categories_breakdown: any[];
}

export interface HrPendingReviewItem {
  id: number;
  employee_id: number;
  employee_name: string;
  employee_code: string;
  department: string;
  document_type_id: number;
  document_type_name: string;
  category: string;
  file_name: string;
  file_size: number;
  mime_type: string;
  version: number;
  status: string;
  uploaded_by_name: string;
  uploaded_by_role: string;
  uploaded_at: string;
  rejection_reason?: string | null;
  remarks?: string | null;
}

export interface HrPendingReviewsResponse {
  data: HrPendingReviewItem[];
  total: number;
  page: number;
  limit: number;
}
