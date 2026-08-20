import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, Subject, tap } from 'rxjs';
import { buildApiUrl } from '../config/api.config';
import {
  DocumentType,
  DocumentVersion,
  EmployeeDocumentsPageResponse,
  HrDocumentOverviewKPI,
  HrPendingReviewsResponse
} from '../models/document.model';

@Injectable({ providedIn: 'root' })
export class DocumentService {
  private readonly baseUrl = buildApiUrl('/documents');

  private readonly documentUpdatedSubject = new Subject<void>();
  public readonly documentUpdated$ = this.documentUpdatedSubject.asObservable();

  constructor(private readonly http: HttpClient) {}

  notifyDocumentUpdated(): void {
    this.documentUpdatedSubject.next();
  }

  // ─── Document Types ────────────────────────────────────────────────────────

  getDocumentTypes(includeInactive: boolean = false): Observable<DocumentType[]> {
    const params = new HttpParams().set('include_inactive', String(includeInactive));
    return this.http.get<DocumentType[]>(`${this.baseUrl}/types`, { params });
  }

  // ─── Employee Document Operations ──────────────────────────────────────────

  getMyDocuments(): Observable<EmployeeDocumentsPageResponse> {
    return this.http.get<EmployeeDocumentsPageResponse>(`${this.baseUrl}/my-documents`);
  }

  uploadMyDocument(documentTypeId: number, file: File, remarks?: string): Observable<any> {
    const formData = new FormData();
    formData.append('document_type_id', String(documentTypeId));
    formData.append('file', file, file.name);
    if (remarks) {
      formData.append('remarks', remarks);
    }

    return this.http.post<any>(`${this.baseUrl}/upload`, formData).pipe(
      tap(() => this.notifyDocumentUpdated())
    );
  }

  // ─── HR Document Operations ────────────────────────────────────────────────

  getEmployeeDocumentsForHr(employeeId: number | string): Observable<EmployeeDocumentsPageResponse> {
    return this.http.get<EmployeeDocumentsPageResponse>(`${this.baseUrl}/hr/employees/${employeeId}`);
  }

  hrUploadDocument(
    employeeId: number | string,
    documentTypeId: number,
    file: File,
    remarks?: string
  ): Observable<any> {
    const formData = new FormData();
    formData.append('document_type_id', String(documentTypeId));
    formData.append('file', file, file.name);
    if (remarks) {
      formData.append('remarks', remarks);
    }

    return this.http.post<any>(`${this.baseUrl}/hr/employees/${employeeId}/upload`, formData).pipe(
      tap(() => this.notifyDocumentUpdated())
    );
  }

  updateEmployeeRequirement(
    employeeId: number | string,
    documentTypeId: number,
    isRequired: boolean,
    dueDate?: string
  ): Observable<any> {
    const payload = {
      document_type_id: documentTypeId,
      is_required: isRequired,
      due_date: dueDate || null
    };
    return this.http.post<any>(`${this.baseUrl}/hr/employees/${employeeId}/requirements`, payload).pipe(
      tap(() => this.notifyDocumentUpdated())
    );
  }

  verifyDocument(documentId: number, remarks?: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/hr/${documentId}/verify`, { remarks }).pipe(
      tap(() => this.notifyDocumentUpdated())
    );
  }

  rejectDocument(documentId: number, reason: string, remarks?: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/hr/${documentId}/reject`, { reason, remarks }).pipe(
      tap(() => this.notifyDocumentUpdated())
    );
  }

  deleteDocument(documentId: number): Observable<any> {
    return this.http.delete<any>(`${this.baseUrl}/hr/${documentId}`).pipe(
      tap(() => this.notifyDocumentUpdated())
    );
  }

  getHrOverview(): Observable<HrDocumentOverviewKPI> {
    return this.http.get<HrDocumentOverviewKPI>(`${this.baseUrl}/hr/overview`);
  }

  getHrPendingReviews(
    page: number = 1,
    limit: number = 10,
    search: string = '',
    department: string = '',
    statusFilter: string = ''
  ): Observable<HrPendingReviewsResponse> {
    let params = new HttpParams()
      .set('page', String(page))
      .set('limit', String(limit));

    if (search.trim()) {
      params = params.set('search', search.trim());
    }
    if (department) {
      params = params.set('department', department);
    }
    if (statusFilter) {
      params = params.set('status_filter', statusFilter);
    }

    return this.http.get<HrPendingReviewsResponse>(`${this.baseUrl}/hr/pending`, { params });
  }

  // ─── Version History & File Streaming ──────────────────────────────────────

  getDocumentHistory(documentId: number): Observable<DocumentVersion[]> {
    return this.http.get<DocumentVersion[]>(`${this.baseUrl}/${documentId}/history`);
  }

  downloadDocument(documentId: number): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/${documentId}/download`, {
      responseType: 'blob'
    });
  }

  previewDocument(documentId: number): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/${documentId}/preview`, {
      responseType: 'blob'
    });
  }

  downloadVersion(versionId: number): Observable<Blob> {
    return this.http.get(`${this.baseUrl}/versions/${versionId}/download`, {
      responseType: 'blob'
    });
  }

  formatFileSize(bytes?: number | null): string {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }
}
